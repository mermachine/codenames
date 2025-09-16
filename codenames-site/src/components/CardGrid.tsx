
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
  <div className="grid grid-cols-5 gap-4">
    {states.flatMap((sts) =>
      sts.map((st) =>
        CardCell({ state: st })))
    }
  </div>

}
