import { Card } from "@/components/ui/card"
import { cn } from "@/lib/utils"
import type { RevealedKind } from "./RevealedCard"

const baseCardClasses = "relative flex h-full w-full flex-col items-center justify-center gap-0 overflow-hidden text-center font-semibold tracking-wide uppercase transition";

const accentMap: Record<RevealedKind, string> = {
  red: "border-[#ff76b2]/55 text-[#ffe3ef] shadow-[0_0_18px_rgba(255,118,178,0.35)] bg-gradient-to-br from-[#30112a]/80 via-[#3c1633]/70 to-[#4f1a3f]/60",
  blue: "border-[#7bd6ff]/55 text-[#e7f8ff] shadow-[0_0_18px_rgba(123,214,255,0.32)] bg-gradient-to-br from-[#102437]/80 via-[#19324a]/70 to-[#21445f]/60",
  assassin: "border-[#8248ff]/55 text-[#f7efff] shadow-[0_0_32px_rgba(130,72,255,0.55)] bg-gradient-to-br from-[#050509]/95 via-[#11111c]/90 to-[#1a1b2b]/80",
  neutral: "border-white/8 text-[#dfe2ff] bg-[#181533]/70"
};

export function WordCard({ word, kind }: { word: string; kind: RevealedKind }) {
  const accent = accentMap[kind] ?? accentMap.neutral;
  const isAssassin = kind === "assassin";

  return (
    <Card
      className={cn(
        baseCardClasses,
        "border backdrop-blur-sm",
        accent,
        kind === "neutral" ? "shadow-[0_0_12px_rgba(115,110,180,0.22)]" : null,
        isAssassin ? "assassin-card" : null
      )}
    >
      <span className="relative z-10 drop-shadow-[0_0_8px_rgba(0,0,0,0.55)]">{word}</span>
    </Card>
  )
}
