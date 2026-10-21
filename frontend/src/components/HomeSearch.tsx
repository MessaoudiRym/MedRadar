"use client";

import { useRef } from "react";

import { PhotoSearch } from "./photo/PhotoSearch";
import { SearchBox } from "./SearchBox";

/** Search by name, or by a photo of the box (when the API can read photos). */
export function HomeSearch() {
  const input = useRef<HTMLInputElement>(null);

  function typeName() {
    input.current?.scrollIntoView({ block: "center", behavior: "smooth" });
    input.current?.focus({ preventScroll: true });
  }

  return (
    <div className="space-y-6">
      <SearchBox inputRef={input} />
      <PhotoSearch onTypeName={typeName} />
    </div>
  );
}
