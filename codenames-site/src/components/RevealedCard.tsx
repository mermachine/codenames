
import { Card } from "@/components/ui/card"
import redSpyImg from '../assets/red_spy.jpeg';
import blueSpyImg from '../assets/blue_spy.jpeg';
import neutralImg from '../assets/neutral.png';
import assassinImg from '../assets/assassin.jpeg'

export type RevealedKind = 'red' | 'blue' | 'neutral' | 'assassin';

export function RevealedCard({ kind }: { kind: RevealedKind }) {
  return <Card>
    <img src={kind == 'red' ? redSpyImg : kind == 'blue' ? blueSpyImg : kind == 'neutral' ? neutralImg : assassinImg} />
  </Card>;

}
