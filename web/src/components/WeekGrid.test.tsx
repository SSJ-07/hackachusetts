import { afterEach, describe, expect, it, vi } from "vitest";
import fc from "fast-check";
import { cleanup, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { WeekGrid } from "./WeekGrid";
import type { AuditCell, Day } from "../api/types";
import { HOURS, blockKey, hourLabel } from "../lib/scale";

/**
 * Property: a SINGLE keyboard move (pick up + drop on a different hour, same
 * day column) calls onMove exactly ONCE, with the picked block key and the
 * destination hour. We generate random from != to to prove it holds for any
 * pair of distinct hours in a day.
 *
 * (A drag/drop alternative is exercised in the e2e suite; jsdom does not run a
 * full HTML5 drag-and-drop, so the unit property uses the keyboard path, which
 * the component documents as the accessible equivalent of one drag.)
 */

afterEach(cleanup);

const DAY: Day = "mon";

/** A full Monday column so every HOURS cell renders. */
function monCells(shareByHour: (hour: number) => number): AuditCell[] {
  return HOURS.map((hour) => {
    const n = 100;
    const reached = Math.round(shareByHour(hour) * n);
    return { day: DAY, hour, share: reached / n, n, reached };
  });
}

async function keyboardMove(
  user: ReturnType<typeof userEvent.setup>,
  fromHour: number,
  toHour: number,
): Promise<void> {
  const fromName = new RegExp(`Monday ${hourLabel(fromHour)}`, "i");
  // Focus the source cell, pick it up, step to the destination, drop.
  const fromBtn = screen.getByRole("button", { name: fromName });
  fromBtn.focus();
  await user.keyboard("{Enter}"); // pick up
  const steps = toHour - fromHour;
  const key = steps > 0 ? "{ArrowDown}" : "{ArrowUp}";
  for (let i = 0; i < Math.abs(steps); i += 1) {
    await user.keyboard(key);
  }
  await user.keyboard("{Enter}"); // drop
}

describe("WeekGrid keyboard move", () => {
  it("calls onMove exactly once for a single move (random from != to)", async () => {
    await fc.assert(
      fc.asyncProperty(
        fc.integer({ min: 0, max: HOURS.length - 1 }),
        fc.integer({ min: 0, max: HOURS.length - 1 }),
        async (i, j) => {
          if (i === j) return; // need from != to
          cleanup();
          const fromHour = HOURS[i];
          const toHour = HOURS[j];
          const onMove = vi.fn();
          const user = userEvent.setup();
          render(
            <table>
              <tbody>
                <tr>
                  <td>
                    <WeekGrid
                      cells={monCells((h) => (h % 3) / 3)}
                      busy={false}
                      pickedBlock={null}
                      onCellFocus={() => {}}
                      onMove={onMove}
                    />
                  </td>
                </tr>
              </tbody>
            </table>,
          );
          await keyboardMove(user, fromHour, toHour);
          expect(onMove).toHaveBeenCalledTimes(1);
          expect(onMove).toHaveBeenCalledWith(blockKey(DAY, fromHour), toHour);
        },
      ),
      { numRuns: 25 },
    );
  });

  it("does not call onMove when dropped on the same hour", async () => {
    const onMove = vi.fn();
    const user = userEvent.setup();
    render(
      <table>
        <tbody>
          <tr>
            <td>
              <WeekGrid
                cells={monCells(() => 0.5)}
                busy={false}
                pickedBlock={null}
                onCellFocus={() => {}}
                onMove={onMove}
              />
            </td>
          </tr>
        </tbody>
      </table>,
    );
    const btn = screen.getByRole("button", {
      name: new RegExp(`Monday ${hourLabel(HOURS[2])}`, "i"),
    });
    btn.focus();
    await user.keyboard("{Enter}"); // pick up
    await user.keyboard("{Enter}"); // drop on same hour
    expect(onMove).not.toHaveBeenCalled();
  });
});
