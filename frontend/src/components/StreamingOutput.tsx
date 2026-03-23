interface Props {
  text: string;
  done: boolean;
}

export function StreamingOutput({ text, done }: Props) {
  return (
    <div className="rounded-lg border bg-muted/30 p-4 text-sm font-mono whitespace-pre-wrap min-h-[6rem]">
      {text || <span className="text-muted-foreground animate-pulse">Waiting for tokens…</span>}
      {!done && text && (
        <span className="inline-block w-2 h-4 bg-foreground ml-0.5 animate-pulse align-middle" />
      )}
    </div>
  );
}
