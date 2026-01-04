import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { renderHook, act } from "@testing-library/react";
import { useLocalStorage } from "./use-local-storage";

describe("useLocalStorage", () => {
  beforeEach(() => {
    // Clear localStorage before each test
    localStorage.clear();
    // Clear console.warn mock
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  describe("initial value", () => {
    it("returns initial value when storage is empty", () => {
      const { result } = renderHook(() =>
        useLocalStorage("test-key", "default-value")
      );

      expect(result.current[0]).toBe("default-value");
    });

    it("returns initial number when storage is empty", () => {
      const { result } = renderHook(() => useLocalStorage("test-key", 42));

      expect(result.current[0]).toBe(42);
    });

    it("returns initial boolean when storage is empty", () => {
      const { result } = renderHook(() => useLocalStorage("test-key", true));

      expect(result.current[0]).toBe(true);
    });

    it("returns initial object when storage is empty", () => {
      const initialObj = { name: "test", count: 1 };
      const { result } = renderHook(() =>
        useLocalStorage("test-key", initialObj)
      );

      expect(result.current[0]).toEqual(initialObj);
    });

    it("returns initial array when storage is empty", () => {
      const initialArray = [1, 2, 3];
      const { result } = renderHook(() =>
        useLocalStorage("test-key", initialArray)
      );

      expect(result.current[0]).toEqual(initialArray);
    });

    it("returns initial null value when storage is empty", () => {
      const { result } = renderHook(() => useLocalStorage("test-key", null));

      expect(result.current[0]).toBe(null);
    });
  });

  describe("reading from localStorage", () => {
    it("reads existing string value from localStorage", () => {
      localStorage.setItem("test-key", JSON.stringify("stored-value"));

      const { result } = renderHook(() =>
        useLocalStorage("test-key", "default-value")
      );

      expect(result.current[0]).toBe("stored-value");
    });

    it("reads existing number value from localStorage", () => {
      localStorage.setItem("test-key", JSON.stringify(100));

      const { result } = renderHook(() => useLocalStorage("test-key", 0));

      expect(result.current[0]).toBe(100);
    });

    it("reads existing boolean value from localStorage", () => {
      localStorage.setItem("test-key", JSON.stringify(false));

      const { result } = renderHook(() => useLocalStorage("test-key", true));

      expect(result.current[0]).toBe(false);
    });

    it("reads existing object value from localStorage", () => {
      const storedObj = { id: 1, name: "stored" };
      localStorage.setItem("test-key", JSON.stringify(storedObj));

      const { result } = renderHook(() =>
        useLocalStorage("test-key", { id: 0, name: "" })
      );

      expect(result.current[0]).toEqual(storedObj);
    });

    it("reads existing array value from localStorage", () => {
      const storedArray = [4, 5, 6];
      localStorage.setItem("test-key", JSON.stringify(storedArray));

      const { result } = renderHook(() => useLocalStorage("test-key", []));

      expect(result.current[0]).toEqual(storedArray);
    });

    it("reads null value from localStorage", () => {
      localStorage.setItem("test-key", JSON.stringify(null));

      const { result } = renderHook(() =>
        useLocalStorage("test-key", "default")
      );

      expect(result.current[0]).toBe(null);
    });

    it("prefers stored value over initial value", () => {
      localStorage.setItem("test-key", JSON.stringify("stored"));

      const { result } = renderHook(() =>
        useLocalStorage("test-key", "initial")
      );

      expect(result.current[0]).toBe("stored");
      expect(result.current[0]).not.toBe("initial");
    });
  });

  describe("writing to localStorage", () => {
    it("updates localStorage when value changes", () => {
      const { result } = renderHook(() =>
        useLocalStorage("test-key", "initial")
      );

      act(() => {
        result.current[1]("updated");
      });

      expect(result.current[0]).toBe("updated");
      expect(localStorage.getItem("test-key")).toBe(JSON.stringify("updated"));
    });

    it("updates localStorage with number value", () => {
      const { result } = renderHook(() => useLocalStorage("test-key", 0));

      act(() => {
        result.current[1](42);
      });

      expect(result.current[0]).toBe(42);
      expect(localStorage.getItem("test-key")).toBe(JSON.stringify(42));
    });

    it("updates localStorage with boolean value", () => {
      const { result } = renderHook(() => useLocalStorage("test-key", false));

      act(() => {
        result.current[1](true);
      });

      expect(result.current[0]).toBe(true);
      expect(localStorage.getItem("test-key")).toBe(JSON.stringify(true));
    });

    it("updates localStorage with object value", () => {
      const newObj = { id: 2, name: "updated" };
      const { result } = renderHook(() =>
        useLocalStorage("test-key", { id: 1, name: "initial" })
      );

      act(() => {
        result.current[1](newObj);
      });

      expect(result.current[0]).toEqual(newObj);
      expect(localStorage.getItem("test-key")).toBe(JSON.stringify(newObj));
    });

    it("updates localStorage with array value", () => {
      const newArray = [4, 5, 6];
      const { result } = renderHook(() => useLocalStorage("test-key", [1, 2]));

      act(() => {
        result.current[1](newArray);
      });

      expect(result.current[0]).toEqual(newArray);
      expect(localStorage.getItem("test-key")).toBe(JSON.stringify(newArray));
    });

    it("updates localStorage with null value", () => {
      const { result } = renderHook(() =>
        useLocalStorage<string | null>("test-key", "initial")
      );

      act(() => {
        result.current[1](null);
      });

      expect(result.current[0]).toBe(null);
      expect(localStorage.getItem("test-key")).toBe(JSON.stringify(null));
    });

    it("persists value across multiple updates", () => {
      const { result } = renderHook(() => useLocalStorage("test-key", 0));

      act(() => {
        result.current[1](1);
      });
      expect(localStorage.getItem("test-key")).toBe(JSON.stringify(1));

      act(() => {
        result.current[1](2);
      });
      expect(localStorage.getItem("test-key")).toBe(JSON.stringify(2));

      act(() => {
        result.current[1](3);
      });
      expect(localStorage.getItem("test-key")).toBe(JSON.stringify(3));

      expect(result.current[0]).toBe(3);
    });
  });

  describe("function updates", () => {
    it("handles function updates with previous value", () => {
      const { result } = renderHook(() => useLocalStorage("test-key", 0));

      act(() => {
        result.current[1]((prev) => prev + 1);
      });

      expect(result.current[0]).toBe(1);
      expect(localStorage.getItem("test-key")).toBe(JSON.stringify(1));
    });

    it("handles multiple function updates in sequence", () => {
      const { result } = renderHook(() => useLocalStorage("test-key", 10));

      act(() => {
        result.current[1]((prev) => prev + 5);
      });
      expect(result.current[0]).toBe(15);

      act(() => {
        result.current[1]((prev) => prev * 2);
      });
      expect(result.current[0]).toBe(30);

      act(() => {
        result.current[1]((prev) => prev - 10);
      });
      expect(result.current[0]).toBe(20);

      expect(localStorage.getItem("test-key")).toBe(JSON.stringify(20));
    });

    it("handles function updates with string values", () => {
      const { result } = renderHook(() =>
        useLocalStorage("test-key", "Hello")
      );

      act(() => {
        result.current[1]((prev) => prev + " World");
      });

      expect(result.current[0]).toBe("Hello World");
      expect(localStorage.getItem("test-key")).toBe(
        JSON.stringify("Hello World")
      );
    });

    it("handles function updates with object values", () => {
      const { result } = renderHook(() =>
        useLocalStorage("test-key", { count: 0, name: "test" })
      );

      act(() => {
        result.current[1]((prev) => ({ ...prev, count: prev.count + 1 }));
      });

      expect(result.current[0]).toEqual({ count: 1, name: "test" });
      expect(localStorage.getItem("test-key")).toBe(
        JSON.stringify({ count: 1, name: "test" })
      );
    });

    it("handles function updates with array values", () => {
      const { result } = renderHook(() => useLocalStorage("test-key", [1, 2]));

      act(() => {
        result.current[1]((prev) => [...prev, 3]);
      });

      expect(result.current[0]).toEqual([1, 2, 3]);
      expect(localStorage.getItem("test-key")).toBe(JSON.stringify([1, 2, 3]));
    });

    it("handles function updates with boolean toggle", () => {
      const { result } = renderHook(() => useLocalStorage("test-key", false));

      act(() => {
        result.current[1]((prev) => !prev);
      });
      expect(result.current[0]).toBe(true);

      act(() => {
        result.current[1]((prev) => !prev);
      });
      expect(result.current[0]).toBe(false);

      expect(localStorage.getItem("test-key")).toBe(JSON.stringify(false));
    });
  });

  describe("JSON parse errors", () => {
    it("returns initial value when stored value is malformed JSON", () => {
      const consoleWarnSpy = vi.spyOn(console, "warn").mockImplementation();
      localStorage.setItem("test-key", "invalid-json{{{");

      const { result } = renderHook(() =>
        useLocalStorage("test-key", "default")
      );

      expect(result.current[0]).toBe("default");
      expect(consoleWarnSpy).toHaveBeenCalledWith(
        expect.stringContaining('Error reading localStorage key "test-key"'),
        expect.any(Error)
      );
    });

    it("returns initial value when stored value is not valid JSON", () => {
      const consoleWarnSpy = vi.spyOn(console, "warn").mockImplementation();
      localStorage.setItem("test-key", "{invalid}");

      const { result } = renderHook(() =>
        useLocalStorage("test-key", "default")
      );

      expect(result.current[0]).toBe("default");
      expect(consoleWarnSpy).toHaveBeenCalled();
    });

    it("returns initial value when stored value is incomplete JSON", () => {
      const consoleWarnSpy = vi.spyOn(console, "warn").mockImplementation();
      localStorage.setItem("test-key", '{"name": "test"');

      const { result } = renderHook(() =>
        useLocalStorage("test-key", { name: "default" })
      );

      expect(result.current[0]).toEqual({ name: "default" });
      expect(consoleWarnSpy).toHaveBeenCalled();
    });

    it("handles storage errors during write gracefully", () => {
      const consoleWarnSpy = vi.spyOn(console, "warn").mockImplementation();
      const setItemSpy = vi
        .spyOn(Storage.prototype, "setItem")
        .mockImplementation(() => {
          throw new Error("Storage quota exceeded");
        });

      const { result } = renderHook(() =>
        useLocalStorage("test-key", "initial")
      );

      act(() => {
        result.current[1]("updated");
      });

      // Value should still update in state even if localStorage fails
      expect(result.current[0]).toBe("updated");
      expect(consoleWarnSpy).toHaveBeenCalledWith(
        expect.stringContaining('Error setting localStorage key "test-key"'),
        expect.any(Error)
      );

      setItemSpy.mockRestore();
    });
  });

  describe("storage persistence", () => {
    it("persists value across hook re-renders", () => {
      const { result, rerender } = renderHook(() =>
        useLocalStorage("test-key", "initial")
      );

      act(() => {
        result.current[1]("updated");
      });

      // Re-render the hook
      rerender();

      expect(result.current[0]).toBe("updated");
      expect(localStorage.getItem("test-key")).toBe(JSON.stringify("updated"));
    });

    it("persists value across hook unmount and remount", () => {
      const { result, unmount } = renderHook(() =>
        useLocalStorage("test-key", "initial")
      );

      act(() => {
        result.current[1]("persisted");
      });

      // Unmount the hook
      unmount();

      // Mount a new instance of the hook
      const { result: result2 } = renderHook(() =>
        useLocalStorage("test-key", "initial")
      );

      // Should read the persisted value
      expect(result2.current[0]).toBe("persisted");
    });

    it("persists complex object across remount", () => {
      const complexObj = {
        user: { id: 1, name: "John", roles: ["admin", "user"] },
        settings: { theme: "dark", notifications: true },
        data: [1, 2, 3, 4, 5],
      };

      const { result, unmount } = renderHook(() =>
        useLocalStorage("test-key", {})
      );

      act(() => {
        result.current[1](complexObj);
      });

      unmount();

      const { result: result2 } = renderHook(() =>
        useLocalStorage("test-key", {})
      );

      expect(result2.current[0]).toEqual(complexObj);
    });

    it("maintains separate storage for different keys", () => {
      const { result: result1 } = renderHook(() =>
        useLocalStorage("key-1", "value-1")
      );
      const { result: result2 } = renderHook(() =>
        useLocalStorage("key-2", "value-2")
      );

      act(() => {
        result1.current[1]("updated-1");
      });

      act(() => {
        result2.current[1]("updated-2");
      });

      expect(result1.current[0]).toBe("updated-1");
      expect(result2.current[0]).toBe("updated-2");
      expect(localStorage.getItem("key-1")).toBe(JSON.stringify("updated-1"));
      expect(localStorage.getItem("key-2")).toBe(JSON.stringify("updated-2"));
    });

    it("updates storage when key changes", () => {
      const { result, rerender } = renderHook(
        ({ key, initialValue }) => useLocalStorage(key, initialValue),
        {
          initialProps: { key: "key-1", initialValue: "value-1" },
        }
      );

      act(() => {
        result.current[1]("updated-1");
      });

      // Change the key
      rerender({ key: "key-2", initialValue: "value-2" });

      // Should read from the new key (which is empty)
      expect(result.current[0]).toBe("value-2");

      // Old key should still have its value
      expect(localStorage.getItem("key-1")).toBe(JSON.stringify("updated-1"));
    });
  });

  describe("different value types", () => {
    it("works with string values", () => {
      const { result } = renderHook(() =>
        useLocalStorage("test-key", "string-value")
      );

      act(() => {
        result.current[1]("new-string");
      });

      expect(result.current[0]).toBe("new-string");
      expect(localStorage.getItem("test-key")).toBe(
        JSON.stringify("new-string")
      );
    });

    it("works with number values including zero", () => {
      const { result } = renderHook(() => useLocalStorage("test-key", 0));

      act(() => {
        result.current[1](42);
      });

      expect(result.current[0]).toBe(42);

      act(() => {
        result.current[1](0);
      });

      expect(result.current[0]).toBe(0);
      expect(localStorage.getItem("test-key")).toBe(JSON.stringify(0));
    });

    it("works with negative numbers", () => {
      const { result } = renderHook(() => useLocalStorage("test-key", 0));

      act(() => {
        result.current[1](-100);
      });

      expect(result.current[0]).toBe(-100);
      expect(localStorage.getItem("test-key")).toBe(JSON.stringify(-100));
    });

    it("works with decimal numbers", () => {
      const { result } = renderHook(() => useLocalStorage("test-key", 0));

      act(() => {
        result.current[1](3.14159);
      });

      expect(result.current[0]).toBe(3.14159);
      expect(localStorage.getItem("test-key")).toBe(JSON.stringify(3.14159));
    });

    it("works with boolean values", () => {
      const { result } = renderHook(() => useLocalStorage("test-key", false));

      act(() => {
        result.current[1](true);
      });

      expect(result.current[0]).toBe(true);
      expect(localStorage.getItem("test-key")).toBe(JSON.stringify(true));
    });

    it("works with null values", () => {
      const { result } = renderHook(() =>
        useLocalStorage<string | null>("test-key", "initial")
      );

      act(() => {
        result.current[1](null);
      });

      expect(result.current[0]).toBe(null);
      expect(localStorage.getItem("test-key")).toBe(JSON.stringify(null));
    });

    it("works with empty strings", () => {
      const { result } = renderHook(() => useLocalStorage("test-key", "text"));

      act(() => {
        result.current[1]("");
      });

      expect(result.current[0]).toBe("");
      expect(localStorage.getItem("test-key")).toBe(JSON.stringify(""));
    });

    it("works with empty arrays", () => {
      const { result } = renderHook(() =>
        useLocalStorage("test-key", [1, 2, 3])
      );

      act(() => {
        result.current[1]([]);
      });

      expect(result.current[0]).toEqual([]);
      expect(localStorage.getItem("test-key")).toBe(JSON.stringify([]));
    });

    it("works with empty objects", () => {
      const { result } = renderHook(() =>
        useLocalStorage("test-key", { name: "test" })
      );

      act(() => {
        result.current[1]({});
      });

      expect(result.current[0]).toEqual({});
      expect(localStorage.getItem("test-key")).toBe(JSON.stringify({}));
    });

    it("works with nested objects", () => {
      const nested = {
        level1: {
          level2: {
            level3: {
              value: "deep",
            },
          },
        },
      };

      const { result } = renderHook(() => useLocalStorage("test-key", {}));

      act(() => {
        result.current[1](nested);
      });

      expect(result.current[0]).toEqual(nested);
      expect(result.current[0].level1.level2.level3.value).toBe("deep");
    });

    it("works with arrays of objects", () => {
      const arrayOfObjects = [
        { id: 1, name: "first" },
        { id: 2, name: "second" },
        { id: 3, name: "third" },
      ];

      const { result } = renderHook(() => useLocalStorage("test-key", []));

      act(() => {
        result.current[1](arrayOfObjects);
      });

      expect(result.current[0]).toEqual(arrayOfObjects);
      expect(result.current[0][1].name).toBe("second");
    });
  });

  describe("edge cases", () => {
    it("handles very long string values", () => {
      const longString = "a".repeat(10000);
      const { result } = renderHook(() => useLocalStorage("test-key", ""));

      act(() => {
        result.current[1](longString);
      });

      expect(result.current[0]).toBe(longString);
      expect(result.current[0].length).toBe(10000);
    });

    it("handles special characters in values", () => {
      const specialChars = '!@#$%^&*()_+-=[]{}|;:",.<>?/~`\n\t\r';
      const { result } = renderHook(() => useLocalStorage("test-key", ""));

      act(() => {
        result.current[1](specialChars);
      });

      expect(result.current[0]).toBe(specialChars);
    });

    it("handles unicode characters", () => {
      const unicode = "Hello 世界 🌍 مرحبا";
      const { result } = renderHook(() => useLocalStorage("test-key", ""));

      act(() => {
        result.current[1](unicode);
      });

      expect(result.current[0]).toBe(unicode);
      expect(localStorage.getItem("test-key")).toBe(JSON.stringify(unicode));
    });

    it("handles special characters in keys", () => {
      const specialKey = "test-key-with-special!@#$%";
      const { result } = renderHook(() =>
        useLocalStorage(specialKey, "value")
      );

      act(() => {
        result.current[1]("updated");
      });

      expect(result.current[0]).toBe("updated");
      expect(localStorage.getItem(specialKey)).toBe(JSON.stringify("updated"));
    });

    it("handles very long key names", () => {
      const longKey = "test-key-" + "a".repeat(1000);
      const { result } = renderHook(() => useLocalStorage(longKey, "value"));

      act(() => {
        result.current[1]("updated");
      });

      expect(result.current[0]).toBe("updated");
      expect(localStorage.getItem(longKey)).toBe(JSON.stringify("updated"));
    });

    it("handles Date objects by converting to string", () => {
      const date = new Date("2024-01-01T00:00:00.000Z");
      const { result } = renderHook(() =>
        useLocalStorage<Date>("test-key", new Date())
      );

      act(() => {
        result.current[1](date);
      });

      // Date gets serialized to ISO string by JSON.stringify
      expect(localStorage.getItem("test-key")).toBe(JSON.stringify(date));
    });

    it("handles rapid consecutive updates", () => {
      const { result } = renderHook(() => useLocalStorage("test-key", 0));

      act(() => {
        for (let i = 1; i <= 100; i++) {
          result.current[1](i);
        }
      });

      expect(result.current[0]).toBe(100);
      expect(localStorage.getItem("test-key")).toBe(JSON.stringify(100));
    });

    it("handles same value updates", () => {
      const { result } = renderHook(() =>
        useLocalStorage("test-key", "same-value")
      );

      act(() => {
        result.current[1]("same-value");
      });

      act(() => {
        result.current[1]("same-value");
      });

      expect(result.current[0]).toBe("same-value");
      expect(localStorage.getItem("test-key")).toBe(
        JSON.stringify("same-value")
      );
    });
  });

  describe("real-world scenarios", () => {
    it("simulates user preferences storage", () => {
      const { result } = renderHook(() =>
        useLocalStorage("user-preferences", {
          theme: "light",
          language: "en",
          notifications: true,
        })
      );

      // User changes theme
      act(() => {
        result.current[1]((prev) => ({ ...prev, theme: "dark" }));
      });

      expect(result.current[0].theme).toBe("dark");

      // User disables notifications
      act(() => {
        result.current[1]((prev) => ({ ...prev, notifications: false }));
      });

      expect(result.current[0]).toEqual({
        theme: "dark",
        language: "en",
        notifications: false,
      });
    });

    it("simulates shopping cart storage", () => {
      const { result } = renderHook(() =>
        useLocalStorage<Array<{ id: number; quantity: number }>>("cart", [])
      );

      // Add item to cart
      act(() => {
        result.current[1]((prev) => [...prev, { id: 1, quantity: 2 }]);
      });

      // Add another item
      act(() => {
        result.current[1]((prev) => [...prev, { id: 2, quantity: 1 }]);
      });

      // Update quantity
      act(() => {
        result.current[1]((prev) =>
          prev.map((item) => (item.id === 1 ? { ...item, quantity: 3 } : item))
        );
      });

      expect(result.current[0]).toEqual([
        { id: 1, quantity: 3 },
        { id: 2, quantity: 1 },
      ]);
    });

    it("simulates form draft storage", () => {
      const { result } = renderHook(() =>
        useLocalStorage("form-draft", {
          title: "",
          content: "",
          tags: [] as string[],
        })
      );

      // User types title
      act(() => {
        result.current[1]((prev) => ({ ...prev, title: "My Blog Post" }));
      });

      // User types content
      act(() => {
        result.current[1]((prev) => ({
          ...prev,
          content: "This is the content...",
        }));
      });

      // User adds tags
      act(() => {
        result.current[1]((prev) => ({
          ...prev,
          tags: ["javascript", "react"],
        }));
      });

      expect(result.current[0]).toEqual({
        title: "My Blog Post",
        content: "This is the content...",
        tags: ["javascript", "react"],
      });

      // Simulate page refresh by unmounting and remounting
      const { unmount } = renderHook(() =>
        useLocalStorage("form-draft", {
          title: "",
          content: "",
          tags: [],
        })
      );
      unmount();

      const { result: result2 } = renderHook(() =>
        useLocalStorage("form-draft", {
          title: "",
          content: "",
          tags: [],
        })
      );

      // Draft should be restored
      expect(result2.current[0]).toEqual({
        title: "My Blog Post",
        content: "This is the content...",
        tags: ["javascript", "react"],
      });
    });

    it("simulates toggle state persistence", () => {
      const { result } = renderHook(() =>
        useLocalStorage("sidebar-collapsed", false)
      );

      // User toggles sidebar
      act(() => {
        result.current[1]((prev) => !prev);
      });

      expect(result.current[0]).toBe(true);

      // Simulate page refresh
      const { unmount } = renderHook(() =>
        useLocalStorage("sidebar-collapsed", false)
      );
      unmount();

      const { result: result2 } = renderHook(() =>
        useLocalStorage("sidebar-collapsed", false)
      );

      // State should be restored
      expect(result2.current[0]).toBe(true);
    });

    it("simulates recent searches storage", () => {
      const { result } = renderHook(() =>
        useLocalStorage<string[]>("recent-searches", [])
      );

      // Add searches (keeping only last 5)
      const addSearch = (search: string) => {
        result.current[1]((prev) => {
          const filtered = prev.filter((s) => s !== search);
          return [search, ...filtered].slice(0, 5);
        });
      };

      act(() => {
        addSearch("react hooks");
      });
      act(() => {
        addSearch("typescript");
      });
      act(() => {
        addSearch("vitest");
      });
      act(() => {
        addSearch("react testing library");
      });
      act(() => {
        addSearch("react hooks"); // Duplicate, should move to top
      });

      expect(result.current[0]).toEqual([
        "react hooks",
        "react testing library",
        "vitest",
        "typescript",
      ]);
    });
  });
});
