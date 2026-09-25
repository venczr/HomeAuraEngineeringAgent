import type { Metadata } from "next";
import { HomeAuraEditor } from "./editor/HomeAuraEditor";

export const metadata: Metadata = {
  title: "HomeAura — редактор тёплого пола",
  description: "Локальный инженерный редактор геометрии водяного тёплого пола.",
};

export default function Home() {
  return <HomeAuraEditor />;
}
