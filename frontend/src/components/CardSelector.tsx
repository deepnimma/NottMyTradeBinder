/**
 * Cascading Game → Set → Card selector.
 * Calls parent callbacks when each level is selected.
 */
import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { getSets, getCardsBySet, SetOut, CardOut } from "../api";

interface Props {
  onCardSelect: (card: CardOut) => void;
}

export default function CardSelector({ onCardSelect }: Props) {
  const [game, setGame] = useState<string>("");
  const [setId, setSetId] = useState<string>("");

  const setsQuery = useQuery({
    queryKey: ["sets", game],
    queryFn: () => getSets(game),
    enabled: !!game,
  });

  const cardsQuery = useQuery({
    queryKey: ["cards", game, setId],
    queryFn: () => getCardsBySet(game, setId),
    enabled: !!game && !!setId,
  });

  const sets: SetOut[] = setsQuery.data ?? [];
  const cards: CardOut[] = cardsQuery.data ?? [];

  return (
    <div className="space-y-3">
      {/* Game */}
      <div>
        <label className="block text-sm text-gray-400 mb-1">Game</label>
        <select
          value={game}
          onChange={(e) => {
            setGame(e.target.value);
            setSetId("");
          }}
          className="w-full bg-gray-800 border border-gray-700 rounded px-3 py-2 text-sm focus:outline-none focus:border-indigo-500"
        >
          <option value="">— Select game —</option>
          <option value="pokemon">Pokémon</option>
          <option value="weiss_schwarz">Weiss Schwarz</option>
        </select>
      </div>

      {/* Set */}
      {game && (
        <div>
          <label className="block text-sm text-gray-400 mb-1">
            Set {setsQuery.isLoading && <span className="text-gray-600">(loading…)</span>}
          </label>
          <select
            value={setId}
            onChange={(e) => setSetId(e.target.value)}
            className="w-full bg-gray-800 border border-gray-700 rounded px-3 py-2 text-sm focus:outline-none focus:border-indigo-500"
            disabled={setsQuery.isLoading || sets.length === 0}
          >
            <option value="">— Select set —</option>
            {sets.map((s) => (
              <option key={s.set_id} value={s.set_id}>
                {s.set_name} ({s.card_count} cards)
              </option>
            ))}
          </select>
        </div>
      )}

      {/* Card */}
      {setId && (
        <div>
          <label className="block text-sm text-gray-400 mb-1">
            Card {cardsQuery.isLoading && <span className="text-gray-600">(loading…)</span>}
          </label>
          <select
            onChange={(e) => {
              const card = cards.find((c) => c.id === Number(e.target.value));
              if (card) onCardSelect(card);
            }}
            className="w-full bg-gray-800 border border-gray-700 rounded px-3 py-2 text-sm focus:outline-none focus:border-indigo-500"
            disabled={cardsQuery.isLoading || cards.length === 0}
            defaultValue=""
          >
            <option value="">— Select card —</option>
            {cards.map((c) => (
              <option key={c.id} value={c.id}>
                {c.card_number && !c.card_number.startsWith("tcg-") ? `#${c.card_number} — ` : ""}
                {c.name}
              </option>
            ))}
          </select>
          {cardsQuery.isLoading && (
            <p className="text-xs text-gray-500 mt-1">Fetching cards from API…</p>
          )}
        </div>
      )}
    </div>
  );
}
