
import { Card } from "@/components/ui/card"
import redSpyImg from '../assets/red_spy.jpeg';
import blueSpyImg from '../assets/blue_spy.jpeg';
import neutralImg from '../assets/neutral.jpeg';
import assassinImg from '../assets/assassin.jpeg'

export type RevealedKind = 'red' | 'blue' | 'neutral' | 'assassin';

export function RevealedCard({ kind }: { kind: RevealedKind }) {
  const image = kind == 'red' ? redSpyImg : kind == 'blue' ? blueSpyImg : kind == 'neutral' ? neutralImg : assassinImg

  return (
    <Card className="h-full w-full overflow-hidden p-0">
      <img
        src={image}
        alt={`${kind} agent`}
        className="h-full w-full object-cover"
      />
    </Card>
  )
}
