import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { renderHook, waitFor } from "@testing-library/react";
import { useDebounce } from "./use-debounce";

describe("useDebounce", () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  describe("initial value", () => {
    it("returns initial value immediately", () => {
      const { result } = renderHook(() => useDebounce("initial", 500));

      expect(result.current).toBe("initial");
    });

    it("returns initial number value immediately", () => {
      const { result } = renderHook(() => useDebounce(42, 500));

      expect(result.current).toBe(42);
    });

    it("returns initial boolean value immediately", () => {
      const { result } = renderHook(() => useDebounce(true, 500));

      expect(result.current).toBe(true);
    });

    it("returns initial object value immediately", () => {
      const initialObj = { name: "test", count: 1 };
      const { result } = renderHook(() => useDebounce(initialObj, 500));

      expect(result.current).toBe(initialObj);
    });

    it("returns initial array value immediately", () => {
      const initialArray = [1, 2, 3];
      const { result } = renderHook(() => useDebounce(initialArray, 500));

      expect(result.current).toBe(initialArray);
    });

    it("returns initial null value immediately", () => {
      const { result } = renderHook(() => useDebounce(null, 500));

      expect(result.current).toBe(null);
    });

    it("returns initial undefined value immediately", () => {
      const { result } = renderHook(() => useDebounce(undefined, 500));

      expect(result.current).toBe(undefined);
    });
  });

  describe("debouncing behavior", () => {
    it("debounces value changes by specified delay", () => {
      const { result, rerender } = renderHook(
        ({ value, delay }) => useDebounce(value, delay),
        { initialProps: { value: "initial", delay: 500 } }
      );

      expect(result.current).toBe("initial");

      // Update the value
      rerender({ value: "updated", delay: 500 });

      // Value should not change immediately
      expect(result.current).toBe("initial");

      // Advance time by 499ms (just before delay)
      vi.advanceTimersByTime(499);
      expect(result.current).toBe("initial");

      // Advance time by 1ms more (total 500ms)
      vi.advanceTimersByTime(1);
      expect(result.current).toBe("updated");
    });

    it("uses default delay of 300ms when not specified", () => {
      const { result, rerender } = renderHook(
        ({ value }) => useDebounce(value),
        { initialProps: { value: "initial" } }
      );

      expect(result.current).toBe("initial");

      rerender({ value: "updated" });

      // Value should not change before 300ms
      vi.advanceTimersByTime(299);
      expect(result.current).toBe("initial");

      // Value should change after 300ms
      vi.advanceTimersByTime(1);
      expect(result.current).toBe("updated");
    });

    it("cancels previous timeout on rapid value changes", () => {
      const { result, rerender } = renderHook(
        ({ value }) => useDebounce(value, 500),
        { initialProps: { value: "initial" } }
      );

      // First update
      rerender({ value: "update1" });
      vi.advanceTimersByTime(200);

      // Second update before first timeout completes
      rerender({ value: "update2" });
      vi.advanceTimersByTime(200);

      // Third update before second timeout completes
      rerender({ value: "update3" });

      // Still showing initial value
      expect(result.current).toBe("initial");

      // Advance to complete the third timeout
      vi.advanceTimersByTime(500);

      // Should show only the latest value
      expect(result.current).toBe("update3");
    });

    it("handles multiple rapid changes and settles on final value", () => {
      const { result, rerender } = renderHook(
        ({ value }) => useDebounce(value, 300),
        { initialProps: { value: 0 } }
      );

      // Simulate rapid typing
      for (let i = 1; i <= 10; i++) {
        rerender({ value: i });
        vi.advanceTimersByTime(50); // Each keystroke 50ms apart
      }

      // Should still show initial value
      expect(result.current).toBe(0);

      // Advance past the delay from the last change
      vi.advanceTimersByTime(300);

      // Should show the final value
      expect(result.current).toBe(10);
    });
  });

  describe("delay changes", () => {
    it("respects delay changes", () => {
      const { result, rerender } = renderHook(
        ({ value, delay }) => useDebounce(value, delay),
        { initialProps: { value: "initial", delay: 500 } }
      );

      // Change both value and delay
      rerender({ value: "updated", delay: 1000 });

      // Advance by old delay (500ms) - should not update yet
      vi.advanceTimersByTime(500);
      expect(result.current).toBe("initial");

      // Advance by remaining time to new delay (500ms more)
      vi.advanceTimersByTime(500);
      expect(result.current).toBe("updated");
    });

    it("handles delay change from longer to shorter", () => {
      const { result, rerender } = renderHook(
        ({ value, delay }) => useDebounce(value, delay),
        { initialProps: { value: "initial", delay: 1000 } }
      );

      // Change to shorter delay
      rerender({ value: "updated", delay: 200 });

      // Should update after the new shorter delay
      vi.advanceTimersByTime(200);
      expect(result.current).toBe("updated");
    });

    it("handles zero delay", () => {
      const { result, rerender } = renderHook(
        ({ value }) => useDebounce(value, 0),
        { initialProps: { value: "initial" } }
      );

      rerender({ value: "updated" });

      // With 0 delay, should update on next tick
      vi.advanceTimersByTime(0);
      expect(result.current).toBe("updated");
    });
  });

  describe("different value types", () => {
    it("works with string values", () => {
      const { result, rerender } = renderHook(
        ({ value }) => useDebounce(value, 300),
        { initialProps: { value: "hello" } }
      );

      rerender({ value: "world" });
      vi.advanceTimersByTime(300);

      expect(result.current).toBe("world");
    });

    it("works with number values", () => {
      const { result, rerender } = renderHook(
        ({ value }) => useDebounce(value, 300),
        { initialProps: { value: 100 } }
      );

      rerender({ value: 200 });
      vi.advanceTimersByTime(300);

      expect(result.current).toBe(200);
    });

    it("works with boolean values", () => {
      const { result, rerender } = renderHook(
        ({ value }) => useDebounce(value, 300),
        { initialProps: { value: false } }
      );

      rerender({ value: true });
      vi.advanceTimersByTime(300);

      expect(result.current).toBe(true);
    });

    it("works with object values", () => {
      const obj1 = { id: 1, name: "first" };
      const obj2 = { id: 2, name: "second" };

      const { result, rerender } = renderHook(
        ({ value }) => useDebounce(value, 300),
        { initialProps: { value: obj1 } }
      );

      rerender({ value: obj2 });
      vi.advanceTimersByTime(300);

      expect(result.current).toBe(obj2);
      expect(result.current.id).toBe(2);
      expect(result.current.name).toBe("second");
    });

    it("works with array values", () => {
      const arr1 = [1, 2, 3];
      const arr2 = [4, 5, 6];

      const { result, rerender } = renderHook(
        ({ value }) => useDebounce(value, 300),
        { initialProps: { value: arr1 } }
      );

      rerender({ value: arr2 });
      vi.advanceTimersByTime(300);

      expect(result.current).toBe(arr2);
      expect(result.current).toEqual([4, 5, 6]);
    });

    it("works with null values", () => {
      const { result, rerender } = renderHook(
        ({ value }) => useDebounce(value, 300),
        { initialProps: { value: "something" as string | null } }
      );

      rerender({ value: null });
      vi.advanceTimersByTime(300);

      expect(result.current).toBe(null);
    });

    it("works with undefined values", () => {
      const { result, rerender } = renderHook(
        ({ value }) => useDebounce(value, 300),
        { initialProps: { value: "something" as string | undefined } }
      );

      rerender({ value: undefined });
      vi.advanceTimersByTime(300);

      expect(result.current).toBe(undefined);
    });
  });

  describe("cleanup behavior", () => {
    it("clears timeout on unmount", () => {
      const clearTimeoutSpy = vi.spyOn(global, "clearTimeout");

      const { rerender, unmount } = renderHook(
        ({ value }) => useDebounce(value, 500),
        { initialProps: { value: "initial" } }
      );

      rerender({ value: "updated" });

      // Unmount before timeout completes
      unmount();

      // clearTimeout should have been called
      expect(clearTimeoutSpy).toHaveBeenCalled();
    });

    it("does not update value after unmount", () => {
      const { result, rerender, unmount } = renderHook(
        ({ value }) => useDebounce(value, 500),
        { initialProps: { value: "initial" } }
      );

      rerender({ value: "updated" });
      const currentValue = result.current;

      // Unmount before timeout completes
      unmount();

      // Advance time past the delay
      vi.advanceTimersByTime(500);

      // Value should not have changed (still the value at unmount)
      expect(currentValue).toBe("initial");
    });

    it("clears previous timeout when value changes", () => {
      const clearTimeoutSpy = vi.spyOn(global, "clearTimeout");

      const { rerender } = renderHook(
        ({ value }) => useDebounce(value, 500),
        { initialProps: { value: "initial" } }
      );

      // First update
      rerender({ value: "update1" });
      const callCount1 = clearTimeoutSpy.mock.calls.length;

      // Second update
      rerender({ value: "update2" });
      const callCount2 = clearTimeoutSpy.mock.calls.length;

      // clearTimeout should have been called again
      expect(callCount2).toBeGreaterThan(callCount1);
    });

    it("clears timeout when delay changes", () => {
      const clearTimeoutSpy = vi.spyOn(global, "clearTimeout");

      const { rerender } = renderHook(
        ({ value, delay }) => useDebounce(value, delay),
        { initialProps: { value: "initial", delay: 500 } }
      );

      rerender({ value: "initial", delay: 1000 });

      // clearTimeout should have been called when delay changed
      expect(clearTimeoutSpy).toHaveBeenCalled();
    });
  });

  describe("edge cases", () => {
    it("handles very long delay values", () => {
      const { result, rerender } = renderHook(
        ({ value }) => useDebounce(value, 10000),
        { initialProps: { value: "initial" } }
      );

      rerender({ value: "updated" });

      // Should not update before delay
      vi.advanceTimersByTime(9999);
      expect(result.current).toBe("initial");

      // Should update after delay
      vi.advanceTimersByTime(1);
      expect(result.current).toBe("updated");
    });

    it("handles same value updates", () => {
      const { result, rerender } = renderHook(
        ({ value }) => useDebounce(value, 300),
        { initialProps: { value: "same" } }
      );

      // Update with the same value
      rerender({ value: "same" });
      vi.advanceTimersByTime(300);

      // Should still have the same value
      expect(result.current).toBe("same");
    });

    it("handles empty string values", () => {
      const { result, rerender } = renderHook(
        ({ value }) => useDebounce(value, 300),
        { initialProps: { value: "text" } }
      );

      rerender({ value: "" });
      vi.advanceTimersByTime(300);

      expect(result.current).toBe("");
    });

    it("handles negative delay by treating it as 0", () => {
      const { result, rerender } = renderHook(
        ({ value }) => useDebounce(value, -100),
        { initialProps: { value: "initial" } }
      );

      rerender({ value: "updated" });

      // With negative delay, setTimeout treats it as 0
      vi.advanceTimersByTime(0);
      expect(result.current).toBe("updated");
    });

    it("handles decimal delay values", () => {
      const { result, rerender } = renderHook(
        ({ value }) => useDebounce(value, 250.5),
        { initialProps: { value: "initial" } }
      );

      rerender({ value: "updated" });

      // Should not update before delay (rounded down by setTimeout)
      vi.advanceTimersByTime(250);
      expect(result.current).toBe("initial");

      // Should update after delay
      vi.advanceTimersByTime(1);
      expect(result.current).toBe("updated");
    });

    it("handles complex nested objects", () => {
      const obj1 = {
        user: { id: 1, profile: { name: "John", age: 30 } },
        settings: { theme: "dark" },
      };
      const obj2 = {
        user: { id: 2, profile: { name: "Jane", age: 25 } },
        settings: { theme: "light" },
      };

      const { result, rerender } = renderHook(
        ({ value }) => useDebounce(value, 300),
        { initialProps: { value: obj1 } }
      );

      rerender({ value: obj2 });
      vi.advanceTimersByTime(300);

      expect(result.current).toBe(obj2);
      expect(result.current.user.profile.name).toBe("Jane");
    });
  });

  describe("real-time scenarios", () => {
    it("simulates search input debouncing", () => {
      const { result, rerender } = renderHook(
        ({ value }) => useDebounce(value, 300),
        { initialProps: { value: "" } }
      );

      // Simulate user typing "react"
      const searchTerm = "react";
      for (let i = 0; i < searchTerm.length; i++) {
        rerender({ value: searchTerm.substring(0, i + 1) });
        vi.advanceTimersByTime(100); // 100ms between keystrokes
      }

      // Should still show empty string
      expect(result.current).toBe("");

      // Advance past the debounce delay from last keystroke
      vi.advanceTimersByTime(300);

      // Should show the complete search term
      expect(result.current).toBe("react");
    });

    it("simulates window resize debouncing", () => {
      const { result, rerender } = renderHook(
        ({ value }) => useDebounce(value, 150),
        { initialProps: { value: { width: 1024, height: 768 } } }
      );

      // Simulate rapid resize events
      const sizes = [
        { width: 1025, height: 769 },
        { width: 1026, height: 770 },
        { width: 1027, height: 771 },
        { width: 1028, height: 772 },
      ];

      sizes.forEach((size) => {
        rerender({ value: size });
        vi.advanceTimersByTime(30);
      });

      // Should still show initial size
      expect(result.current).toEqual({ width: 1024, height: 768 });

      // Advance past debounce delay
      vi.advanceTimersByTime(150);

      // Should show the final size
      expect(result.current).toEqual({ width: 1028, height: 772 });
    });

    it("simulates form input validation debouncing", () => {
      const { result, rerender } = renderHook(
        ({ value }) => useDebounce(value, 500),
        { initialProps: { value: "" } }
      );

      // User starts typing email
      rerender({ value: "j" });
      vi.advanceTimersByTime(100);

      rerender({ value: "jo" });
      vi.advanceTimersByTime(100);

      rerender({ value: "joh" });
      vi.advanceTimersByTime(100);

      rerender({ value: "john" });
      vi.advanceTimersByTime(100);

      rerender({ value: "john@" });
      vi.advanceTimersByTime(100);

      rerender({ value: "john@example.com" });

      // Should not have updated yet
      expect(result.current).toBe("");

      // Wait for debounce
      vi.advanceTimersByTime(500);

      // Should show final email
      expect(result.current).toBe("john@example.com");
    });
  });
});
