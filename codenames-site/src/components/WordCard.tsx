import { Card } from "@/components/ui/card"

export function WordCard({ word }: { word: string }) {
  return (
    <Card className="h-full w-full items-center justify-center text-center">
      {word}
    </Card>
  )
}
