import P8MobileLab, { type P8Direction } from "./P8MobileLab";

type SearchParams = Promise<Record<string, string | string[] | undefined>>;

const DIRECTIONS = new Set<P8Direction>(["web-copy", "web-near", "web-air"]);

export default async function P8MobileArtLabPage({ searchParams }: { searchParams: SearchParams }) {
  const params = await searchParams;
  const requestedDirection = typeof params.direction === "string" ? params.direction : "web-copy";
  const direction = DIRECTIONS.has(requestedDirection as P8Direction)
    ? requestedDirection as P8Direction
    : "web-copy";

  return <P8MobileLab
    direction={direction}
    motion={params.motion !== "off"}
    reference={params.reference === "web"}
    chrome={params.chrome === "1"}
    embedded={params.embedded === "1"}
  />;
}
