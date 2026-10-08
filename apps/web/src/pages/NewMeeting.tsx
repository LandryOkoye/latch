import { ArrowRight, FileText, Sparkle } from "@phosphor-icons/react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useId, useState } from "react";
import { Link } from "react-router-dom";
import { StakesLabel, WindowBadge } from "../components/Badges";
import { Button, Card, EmptyState, PageHeader } from "../components/ui";
import { api } from "../lib/api";
import { formatDate } from "../lib/format";

const SAMPLE = `TITLE: Spring launch check-in
PARTICIPANTS:
- Alex Rivera <alex@northwind.example>
- Tom Becker <tom@harborprint.example>
- Nina Park <nina@lumenstudio.example>
---
[00:00] Alex Rivera: Quick one today. Tom, where are we on the printed banners?
[00:09] Tom Becker: Files are approved. I'll get the printed banners delivered to your office by Thursday.
[00:21] Alex Rivera: Great. Nina, how's the launch video coming along?
[00:27] Nina Park: Still editing. I'll send you a rough cut once the voiceover comes back.
[00:40] Alex Rivera: Perfect. On my side, I'll send you both the final launch schedule by end of day tomorrow.
[00:52] Nina Park: We should probably think about a teaser campaign at some point.
[01:01] Alex Rivera: Maybe, let's park that for now. Thanks, both.`;

export function NewMeeting() {
  const fieldId = useId();
  const helpId = useId();
  const [text, setText] = useState("");
  const queryClient = useQueryClient();
  const ingest = useMutation({
    mutationFn: () => api.ingest(text),
    onSuccess: () => queryClient.invalidateQueries(),
  });

  return (
    <div className="flex flex-col gap-8">
      <PageHeader
        eyebrow="New meeting"
        title="Turn a conversation into tracked loops"
        description="Paste a transcript. The Extractor reads the whole conversation and pulls out every real commitment anyone made, including ones you made yourself."
      />

      <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_minmax(0,0.9fr)]">
        <form
          className="flex flex-col gap-3"
          onSubmit={(event) => {
            event.preventDefault();
            ingest.mutate();
          }}
        >
          <div className="flex items-end justify-between gap-3">
            <label htmlFor={fieldId} className="text-sm font-medium text-ink">
              Transcript
            </label>
            <Button type="button" variant="ghost" icon={FileText} onClick={() => setText(SAMPLE)} className="h-8 px-2.5">
              Load sample
            </Button>
          </div>
          <textarea
            id={fieldId}
            aria-describedby={helpId}
            value={text}
            onChange={(event) => setText(event.target.value)}
            rows={16}
            spellCheck={false}
            placeholder={"[00:09] Tom Becker: I'll get the banners to you by Thursday."}
            className="w-full resize-y rounded-xl border border-line-strong bg-surface px-3.5 py-3 font-mono text-[0.8125rem] leading-relaxed text-ink placeholder:text-ink-3 focus:border-ink focus:outline-none"
          />
          <p id={helpId} className="text-sm text-ink-3">
            One line per utterance, like <code className="font-mono text-ink-2">[00:38] Name: what they said</code>. An optional header
            with <code className="font-mono text-ink-2">TITLE:</code> and a <code className="font-mono text-ink-2">PARTICIPANTS:</code>{" "}
            list (with emails) ends at a <code className="font-mono text-ink-2">---</code> line. The sample includes one near-miss that
            should not be extracted.
          </p>
          <p className="text-sm text-ink-3">
            To see the whole loop, put your own email next to a speaker who makes a promise. When you run the Pursuer on that loop
            you'll get a real follow-up, and Latch will judge whatever you reply.
          </p>
          <Button type="submit" variant="primary" icon={Sparkle} loading={ingest.isPending} disabled={!text.trim()} className="self-start">
            {ingest.isPending ? "Extracting…" : "Extract commitments"}
          </Button>
          {ingest.isError && (
            <p role="alert" className="text-sm text-crit">
              {ingest.error.message}
            </p>
          )}
        </form>

        <section aria-labelledby="extracted-heading" aria-live="polite" className="flex flex-col gap-3">
          <h2 id="extracted-heading" className="text-sm font-medium text-ink">
            Extracted loops
          </h2>
          {!ingest.data ? (
            <Card>
              <EmptyState icon={Sparkle} title={ingest.isPending ? "Reading the conversation…" : "Nothing extracted yet"}>
                {ingest.isPending
                  ? "The Extractor is working through every line. This takes a few seconds."
                  : "Extracted commitments appear here and join the worklist."}
              </EmptyState>
            </Card>
          ) : ingest.data.loops.length === 0 ? (
            <Card>
              <EmptyState icon={Sparkle} title="No commitments found">
                Suggestions like “we should look at that sometime” are deliberately ignored. Only real promises become loops.
              </EmptyState>
            </Card>
          ) : (
            <ul className="flex flex-col gap-3">
              {ingest.data.loops.map((loop) => (
                <li key={loop.id}>
                  <Card className="px-4 py-3.5">
                    <div className="flex items-start justify-between gap-3">
                      <p className="font-medium text-ink">{loop.promise}</p>
                      <WindowBadge source={loop.window_source} />
                    </div>
                    <p className="mt-1 text-sm text-ink-2">“{loop.source_quote}”</p>
                    <div className="mt-3 flex flex-wrap items-center gap-x-4 gap-y-1 text-sm text-ink-2">
                      <span>
                        {loop.owner_name} · <span className="text-ink-3">{loop.counterparty_org}</span>
                      </span>
                      <span>Due {formatDate(loop.due_at)}</span>
                      <StakesLabel stakes={loop.stakes} />
                    </div>
                    <Link
                      to={`/loops/${loop.id}`}
                      className="mt-3 inline-flex items-center gap-1 text-sm font-medium text-ink underline-offset-4 hover:underline"
                    >
                      Open in worklist <ArrowRight size={14} weight="bold" aria-hidden="true" />
                    </Link>
                  </Card>
                </li>
              ))}
            </ul>
          )}
        </section>
      </div>
    </div>
  );
}
