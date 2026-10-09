"""Deploy Latch's production web tier. Idempotent: safe to re-run.

Creates or updates: the DynamoDB ledger table, the Secrets Manager secret (from
your local .env), IAM roles, an ECR repo, a CodeBuild project that builds the
API + web image from the repo, and an ECS Express Mode service that serves it at
a public HTTPS URL. Also grants the AgentCore runtime access to the ledger and
secret. The agent runtime itself is redeployed separately with `agentcore deploy`
(see README).

Usage: .venv/bin/python infra/deploy.py
"""

import io
import json
import os
import subprocess
import sys
import time
import urllib.request
import zipfile
from pathlib import Path

import boto3
from botocore.exceptions import ClientError
from dotenv import dotenv_values

REGION = "us-east-1"
TABLE = "latch-ledger"
SECRET = "latch/prod"
SERVICE = "latch-web"
ECR_REPO = "latch-web"
LOG_GROUP = "/ecs/latch-web"
AGENTCORE_RUNTIME_ID = "latch_agent-CnvTopGvdT"
AGENTCORE_EXECUTION_ROLE = "AmazonBedrockAgentCoreSDKRuntime-us-east-1-010527a71e"
SECRET_KEYS = ["GMAIL_ADDRESS", "GMAIL_APP_PASSWORD", "SHEET_ID", "TELEGRAM_BOT_TOKEN", "TELEGRAM_CHAT_ID"]

ROOT = Path(__file__).resolve().parents[1]
session = boto3.Session(region_name=REGION)
ACCOUNT = session.client("sts").get_caller_identity()["Account"]
iam = session.client("iam")


def step(message: str) -> None:
    print(f"\n==> {message}", flush=True)


def ensure_table() -> str:
    step(f"DynamoDB table {TABLE}")
    os.environ["LATCH_DYNAMODB_TABLE"] = TABLE
    sys.path.insert(0, str(ROOT / "packages/core/src"))
    from latch_core import ledger_dynamodb

    ledger_dynamodb.init_db()
    return session.client("dynamodb").describe_table(TableName=TABLE)["Table"]["TableArn"]


def ensure_secret() -> str:
    step(f"Secret {SECRET} (from .env)")
    env = dotenv_values(ROOT / ".env")
    values = {k: env[k] for k in SECRET_KEYS if env.get(k)}
    key_file = env.get("GOOGLE_SERVICE_ACCOUNT_JSON")
    if key_file and Path(key_file).is_file():
        values["GOOGLE_SERVICE_ACCOUNT_INFO"] = Path(key_file).read_text()
    secrets = session.client("secretsmanager")
    try:
        arn = secrets.create_secret(Name=SECRET, SecretString=json.dumps(values))["ARN"]
    except secrets.exceptions.ResourceExistsException:
        arn = secrets.put_secret_value(SecretId=SECRET, SecretString=json.dumps(values))["ARN"]
    print(f"   keys: {sorted(values)}")
    return arn


def ensure_role(name: str, service: str, managed: list[str] = (), inline: dict | None = None) -> str:
    trust = {"Version": "2012-10-17", "Statement": [{"Effect": "Allow", "Principal": {"Service": service}, "Action": "sts:AssumeRole"}]}
    try:
        arn = iam.create_role(RoleName=name, AssumeRolePolicyDocument=json.dumps(trust))["Role"]["Arn"]
        time.sleep(10)  # IAM propagation before first use
    except iam.exceptions.EntityAlreadyExistsException:
        arn = iam.get_role(RoleName=name)["Role"]["Arn"]
    for policy in managed:
        iam.attach_role_policy(RoleName=name, PolicyArn=policy)
    if inline:
        iam.put_role_policy(RoleName=name, PolicyName=f"{name}-inline", PolicyDocument=json.dumps(inline))
    return arn


def policy(*statements: tuple[list[str], list[str]]) -> dict:
    return {"Version": "2012-10-17", "Statement": [{"Effect": "Allow", "Action": a, "Resource": r} for a, r in statements]}


def ensure_roles(table_arn: str, secret_arn: str, runtime_arn: str) -> dict:
    step("IAM roles")
    data = (["dynamodb:GetItem", "dynamodb:PutItem", "dynamodb:UpdateItem", "dynamodb:DeleteItem", "dynamodb:Query",
             "dynamodb:Scan", "dynamodb:BatchWriteItem", "dynamodb:DescribeTable"], [table_arn, f"{table_arn}/index/*"])
    list_tables = (["dynamodb:ListTables"], ["*"])
    iam.put_role_policy(
        RoleName=AGENTCORE_EXECUTION_ROLE,
        PolicyName="latch-ledger-and-secret",
        PolicyDocument=json.dumps(policy(data, list_tables, (["secretsmanager:GetSecretValue"], [secret_arn]))),
    )
    roles = {
        "task": ensure_role("latch-web-task", "ecs-tasks.amazonaws.com", inline=policy(
            data, list_tables, (["bedrock-agentcore:InvokeAgentRuntime"], [runtime_arn, f"{runtime_arn}/*"]))),
        "execution": ensure_role("latch-web-execution", "ecs-tasks.amazonaws.com",
                                 managed=["arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"]),
        # The managed policy alone was denied these calls during provisioning (seen in CloudTrail).
        "infrastructure": ensure_role("latch-web-infrastructure", "ecs.amazonaws.com",
                                      managed=["arn:aws:iam::aws:policy/service-role/AmazonECSInfrastructureRoleforExpressGatewayServices"],
                                      inline=policy(
                                          (["ecs:UpdateService", "ecs:DescribeServices"], [f"arn:aws:ecs:{REGION}:{ACCOUNT}:service/default/{SERVICE}"]),
                                          (["cloudwatch:DescribeAlarms", "ec2:DescribeAccountAttributes"], ["*"]))),
    }
    for name, arn in roles.items():
        print(f"   {name}: {arn}")
    return roles


def ensure_repo() -> str:
    step(f"ECR repository {ECR_REPO}")
    ecr = session.client("ecr")
    try:
        return ecr.create_repository(repositoryName=ECR_REPO)["repository"]["repositoryUri"]
    except ecr.exceptions.RepositoryAlreadyExistsException:
        return ecr.describe_repositories(repositoryNames=[ECR_REPO])["repositories"][0]["repositoryUri"]


def source_zip() -> bytes:
    files = subprocess.run(["git", "ls-files", "-co", "--exclude-standard"], cwd=ROOT, capture_output=True, text=True, check=True).stdout.split()
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        for name in files:
            if (ROOT / name).is_file():
                archive.write(ROOT / name, name)
    return buffer.getvalue()


BUILDSPEC = """version: 0.2
phases:
  pre_build:
    commands:
      - aws ecr get-login-password --region $AWS_DEFAULT_REGION | docker login --username AWS --password-stdin ${REPO%%/*}
  build:
    commands:
      - docker build -f services/api/Dockerfile -t $REPO:$TAG -t $REPO:latest .
  post_build:
    commands:
      - docker push $REPO:$TAG
      - docker push $REPO:latest
"""


def build_image(repo_uri: str) -> str:
    step("Build image in CodeBuild")
    bucket = f"latch-build-{ACCOUNT}-{REGION}"
    s3 = session.client("s3")
    try:
        s3.create_bucket(Bucket=bucket)
        s3.put_public_access_block(Bucket=bucket, PublicAccessBlockConfiguration={k: True for k in (
            "BlockPublicAcls", "IgnorePublicAcls", "BlockPublicPolicy", "RestrictPublicBuckets")})
    except (s3.exceptions.BucketAlreadyOwnedByYou, s3.exceptions.BucketAlreadyExists):
        pass
    tag = time.strftime("%Y%m%d%H%M%S")
    s3.put_object(Bucket=bucket, Key="latch-web/source.zip", Body=source_zip())

    role = ensure_role("latch-web-codebuild", "codebuild.amazonaws.com", inline=policy(
        (["logs:CreateLogGroup", "logs:CreateLogStream", "logs:PutLogEvents"], ["*"]),
        (["s3:GetObject", "s3:GetObjectVersion"], [f"arn:aws:s3:::{bucket}/*"]),
        (["ecr:GetAuthorizationToken"], ["*"]),
        (["ecr:BatchCheckLayerAvailability", "ecr:InitiateLayerUpload", "ecr:UploadLayerPart", "ecr:CompleteLayerUpload",
          "ecr:PutImage", "ecr:BatchGetImage"], [f"arn:aws:ecr:{REGION}:{ACCOUNT}:repository/{ECR_REPO}"]),
    ))
    codebuild = session.client("codebuild")
    project = dict(
        name="latch-web-builder",
        source={"type": "S3", "location": f"{bucket}/latch-web/source.zip", "buildspec": BUILDSPEC},
        artifacts={"type": "NO_ARTIFACTS"},
        environment={"type": "LINUX_CONTAINER", "image": "aws/codebuild/standard:7.0", "computeType": "BUILD_GENERAL1_MEDIUM",
                     "privilegedMode": True, "environmentVariables": [{"name": "REPO", "value": repo_uri}]},
        serviceRole=role,
    )
    for attempt in range(6):
        try:
            try:
                codebuild.create_project(**project)
            except codebuild.exceptions.ResourceAlreadyExistsException:
                codebuild.update_project(**project)
            break
        except ClientError as error:  # a just-created role may not be assumable yet
            if "not authorized to perform: sts:AssumeRole" not in str(error) or attempt == 5:
                raise
            time.sleep(10)

    for attempt in range(4):
        build_id = codebuild.start_build(projectName="latch-web-builder",
                                         environmentVariablesOverride=[{"name": "TAG", "value": tag}])["build"]["id"]
        while True:
            build = codebuild.batch_get_builds(ids=[build_id])["builds"][0]
            print(f"   {build['currentPhase']:<14} {build['buildStatus']}", flush=True)
            if build["buildStatus"] != "IN_PROGRESS":
                break
            time.sleep(20)
        # A role policy attached seconds ago may not have propagated yet: the
        # build then fails while queued, before it runs anything. Retry that case.
        queued_error = any(p["phaseType"] == "QUEUED" and p.get("phaseStatus") == "CLIENT_ERROR" for p in build["phases"])
        if not (queued_error and attempt < 3):
            break
        print("   role not ready yet, retrying", flush=True)
        time.sleep(20)
    if build["buildStatus"] != "SUCCEEDED":
        for phase in build["phases"]:
            for context in phase.get("contexts", []):
                if context.get("message"):
                    print(f"   {phase['phaseType']}: {context['message']}")
        logs = build.get("logs", {})
        if logs.get("groupName"):
            events = session.client("logs").get_log_events(logGroupName=logs["groupName"], logStreamName=logs["streamName"], limit=60)
            print("\n".join(e["message"].rstrip() for e in events["events"]))
        raise SystemExit("image build failed")
    return f"{repo_uri}:{tag}"


def deploy_service(image: str, roles: dict, runtime_arn: str) -> None:
    step(f"ECS Express service {SERVICE}")
    # On an account's first use of ECS/ELB/autoscaling these service-linked roles
    # don't exist yet, and provisioning fails if it has to race to create them.
    for service_name in ("ecs.amazonaws.com", "elasticloadbalancing.amazonaws.com", "ecs.application-autoscaling.amazonaws.com"):
        try:
            iam.create_service_linked_role(AWSServiceName=service_name)
            time.sleep(10)
        except iam.exceptions.InvalidInputException:
            pass
    logs = session.client("logs")
    try:
        logs.create_log_group(logGroupName=LOG_GROUP)
        logs.put_retention_policy(logGroupName=LOG_GROUP, retentionInDays=14)
    except logs.exceptions.ResourceAlreadyExistsException:
        pass
    ecs = session.client("ecs")
    container = {
        "image": image,
        "containerPort": 8000,
        "awsLogsConfiguration": {"logGroup": LOG_GROUP, "logStreamPrefix": "web"},
        "environment": [
            {"name": "AWS_REGION", "value": REGION},
            {"name": "LATCH_DYNAMODB_TABLE", "value": TABLE},
            {"name": "AGENTCORE_RUNTIME_ARN", "value": runtime_arn},
            {"name": "LATCH_RUN_SCHEDULER", "value": "1"},
        ],
    }
    # One task: it runs the scheduler and holds the demo's in-memory rate limits.
    common = dict(executionRoleArn=roles["execution"], taskRoleArn=roles["task"], primaryContainer=container,
                  healthCheckPath="/api/health", cpu="512", memory="1024",
                  scalingTarget={"minTaskCount": 1, "maxTaskCount": 1, "autoScalingMetric": "AVERAGE_CPU", "autoScalingTargetValue": 70})
    service_arn = f"arn:aws:ecs:{REGION}:{ACCOUNT}:service/default/{SERVICE}"
    try:
        existing = ecs.describe_express_gateway_service(serviceArn=service_arn)["service"]
        exists = existing["status"]["statusCode"] != "INACTIVE"
    except ClientError:
        exists = False
    if exists:
        ecs.update_express_gateway_service(serviceArn=service_arn, **common)
    else:
        service_arn = ecs.create_express_gateway_service(serviceName=SERVICE, infrastructureRoleArn=roles["infrastructure"], **common)["service"]["serviceArn"]

    wait_until_live(ecs, service_arn)


def wait_until_live(ecs, service_arn: str) -> None:
    """The Express service reads ACTIVE before its rollout has even started, so
    wait on the underlying ECS deployment and then the public health check."""
    time.sleep(15)
    while True:
        service = ecs.describe_services(cluster="default", services=[SERVICE])["services"][0]
        primary = next(d for d in service["deployments"] if d["status"] == "PRIMARY")
        print(f"   rollout {primary.get('rolloutState')} running={service['runningCount']}", flush=True)
        if primary.get("rolloutState") == "FAILED":
            raise SystemExit(f"deployment failed: {primary.get('rolloutStateReason')}")
        if primary.get("rolloutState") == "COMPLETED" and service["runningCount"] >= 1:
            break
        time.sleep(20)

    express = ecs.describe_express_gateway_service(serviceArn=service_arn)["service"]
    endpoint = next(p["endpoint"] for c in express["activeConfigurations"] for p in c.get("ingressPaths", []))
    url = endpoint if endpoint.startswith("http") else f"https://{endpoint}"
    for _ in range(60):
        try:
            with urllib.request.urlopen(f"{url}/api/health", timeout=10) as response:
                if response.status == 200:
                    break
        except OSError:
            pass
        time.sleep(10)
    else:
        raise SystemExit(f"{url} never became healthy")
    print(f"\nLive at {url}")


def main() -> None:
    runtime_arn = f"arn:aws:bedrock-agentcore:{REGION}:{ACCOUNT}:runtime/{AGENTCORE_RUNTIME_ID}"
    table_arn = ensure_table()
    secret_arn = ensure_secret()
    roles = ensure_roles(table_arn, secret_arn, runtime_arn)
    image = build_image(ensure_repo())
    deploy_service(image, roles, runtime_arn)


if __name__ == "__main__":
    main()
