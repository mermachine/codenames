import { WordCard } from './WordCard';
import type { RevealedKind } from './RevealedCard';
import { RevealedCard } from './RevealedCard';

export type CardState = {
  word: string,
  kind: RevealedKind,
  isRevealed: boolean
};

function CardCell({ state }: { state: CardState }) {
  if (state.isRevealed) {
    return <RevealedCard kind={state.kind} />;
  } else {
    return <WordCard word={state.word} />;
  }
}

export function CardGrid({ states }: { states: CardState[][] }) {
  return (
    <div className="grid grid-cols-5 gap-4">
      {states.flatMap((sts, rowIdx) =>
        sts.map((st, colIdx) =>
          <CardCell key={`${rowIdx}-${colIdx}-${st.word}`} state={st} />))}
    </div>
  );
}
