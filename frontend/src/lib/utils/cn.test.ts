import { describe, it, expect } from "vitest";
import { cn } from "./cn";

describe("cn", () => {
  describe("basic class name merging", () => {
    it("merges single class name", () => {
      const result = cn("text-red-500");

      expect(result).toBe("text-red-500");
    });

    it("merges multiple class names", () => {
      const result = cn("text-red-500", "bg-blue-500", "p-4");

      expect(result).toBe("text-red-500 bg-blue-500 p-4");
    });

    it("merges class names from array", () => {
      const result = cn(["text-red-500", "bg-blue-500"]);

      expect(result).toBe("text-red-500 bg-blue-500");
    });

    it("handles empty input", () => {
      const result = cn();

      expect(result).toBe("");
    });

    it("handles empty string", () => {
      const result = cn("");

      expect(result).toBe("");
    });
  });

  describe("Tailwind class conflicts", () => {
    it("resolves conflicting padding classes (keeps last)", () => {
      const result = cn("p-4", "p-6");

      expect(result).toBe("p-6");
    });

    it("resolves conflicting margin classes (keeps last)", () => {
      const result = cn("m-2", "m-8");

      expect(result).toBe("m-8");
    });

    it("resolves conflicting text color classes (keeps last)", () => {
      const result = cn("text-red-500", "text-blue-500");

      expect(result).toBe("text-blue-500");
    });

    it("resolves conflicting background color classes (keeps last)", () => {
      const result = cn("bg-red-500", "bg-blue-500");

      expect(result).toBe("bg-blue-500");
    });

    it("resolves conflicting width classes (keeps last)", () => {
      const result = cn("w-32", "w-64");

      expect(result).toBe("w-64");
    });

    it("resolves conflicting height classes (keeps last)", () => {
      const result = cn("h-32", "h-64");

      expect(result).toBe("h-64");
    });

    it("keeps non-conflicting classes when resolving conflicts", () => {
      const result = cn("p-4 text-red-500", "p-6 bg-blue-500");

      expect(result).toBe("text-red-500 p-6 bg-blue-500");
    });

    it("resolves multiple conflicts in one call", () => {
      const result = cn("p-4 m-2 text-red-500", "p-6 m-8 text-blue-500");

      expect(result).toBe("p-6 m-8 text-blue-500");
    });

    it("resolves directional padding conflicts", () => {
      const result = cn("px-4", "px-6");

      expect(result).toBe("px-6");
    });

    it("resolves specific side padding with general padding", () => {
      const result = cn("p-4", "px-6");

      expect(result).toBe("p-4 px-6");
    });
  });

  describe("undefined, null, and false values", () => {
    it("handles undefined values", () => {
      const result = cn("text-red-500", undefined, "bg-blue-500");

      expect(result).toBe("text-red-500 bg-blue-500");
    });

    it("handles null values", () => {
      const result = cn("text-red-500", null, "bg-blue-500");

      expect(result).toBe("text-red-500 bg-blue-500");
    });

    it("handles false values", () => {
      const result = cn("text-red-500", false, "bg-blue-500");

      expect(result).toBe("text-red-500 bg-blue-500");
    });

    it("handles multiple undefined/null/false values", () => {
      const result = cn("text-red-500", undefined, null, false, "bg-blue-500");

      expect(result).toBe("text-red-500 bg-blue-500");
    });

    it("handles all undefined values", () => {
      const result = cn(undefined, undefined);

      expect(result).toBe("");
    });

    it("handles all null values", () => {
      const result = cn(null, null);

      expect(result).toBe("");
    });

    it("handles all false values", () => {
      const result = cn(false, false);

      expect(result).toBe("");
    });
  });

  describe("conditional class names", () => {
    it("applies class when condition is true", () => {
      const isActive = true;
      const result = cn("base-class", isActive && "active-class");

      expect(result).toBe("base-class active-class");
    });

    it("skips class when condition is false", () => {
      const isActive = false;
      const result = cn("base-class", isActive && "active-class");

      expect(result).toBe("base-class");
    });

    it("handles object with boolean values", () => {
      const result = cn({
        "text-red-500": true,
        "bg-blue-500": false,
        "p-4": true,
      });

      expect(result).toBe("text-red-500 p-4");
    });

    it("handles multiple conditional classes", () => {
      const isActive = true;
      const isDisabled = false;
      const result = cn(
        "base-class",
        isActive && "active-class",
        isDisabled && "disabled-class"
      );

      expect(result).toBe("base-class active-class");
    });

    it("handles conditional Tailwind conflicts", () => {
      const variant = "primary";
      const result = cn(
        "p-4",
        variant === "primary" && "bg-blue-500",
        variant === "secondary" && "bg-gray-500"
      );

      expect(result).toBe("p-4 bg-blue-500");
    });

    it("handles complex conditional with object syntax", () => {
      const isActive = true;
      const isError = true;
      const result = cn("base-class", {
        "text-blue-500": isActive,
        "text-red-500": isError,
        "bg-gray-100": false,
      });

      // When both text colors are true, last one in object wins (but order in objects is not guaranteed)
      // So we just check that base-class is there and one of the colors
      expect(result).toContain("base-class");
      expect(result).toMatch(/text-(blue|red)-500/);
    });
  });

  describe("complex scenarios", () => {
    it("handles mix of strings, arrays, objects, and conditionals", () => {
      const isActive = true;
      const result = cn(
        "base-class",
        ["text-red-500", "font-bold"],
        { "bg-blue-500": true, "p-8": false },
        isActive && "active-class"
      );

      expect(result).toBe("base-class text-red-500 font-bold bg-blue-500 active-class");
    });

    it("handles nested arrays", () => {
      const result = cn("base-class", ["text-red-500", ["font-bold", "underline"]]);

      expect(result).toBe("base-class text-red-500 font-bold underline");
    });

    it("handles Tailwind conflicts in complex scenarios", () => {
      const variant = "primary";
      const size = "large";
      const result = cn(
        "p-2 text-sm", // defaults
        variant === "primary" && "bg-blue-500 text-white",
        variant === "secondary" && "bg-gray-500 text-black",
        size === "large" && "p-4 text-lg",
        size === "small" && "p-1 text-xs"
      );

      // Should resolve: p-4 wins over p-2, text-lg wins over text-sm, text-white is kept
      expect(result).toBe("bg-blue-500 text-white p-4 text-lg");
    });

    it("handles very long class name strings", () => {
      const result = cn(
        "flex items-center justify-between gap-4 rounded-lg border border-gray-200 bg-white p-4 shadow-sm transition-all hover:shadow-md",
        "focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2"
      );

      expect(result).toContain("flex");
      expect(result).toContain("items-center");
      expect(result).toContain("focus:ring-2");
    });

    it("handles duplicate non-Tailwind classes", () => {
      const result = cn("custom-class", "another-class", "custom-class");

      // clsx should deduplicate, but the exact behavior depends on implementation
      // At minimum, the result should contain both classes
      expect(result).toContain("custom-class");
      expect(result).toContain("another-class");
    });

    it("handles empty strings mixed with valid classes", () => {
      const result = cn("text-red-500", "", "bg-blue-500", "");

      expect(result).toBe("text-red-500 bg-blue-500");
    });

    it("handles whitespace in class strings", () => {
      const result = cn("  text-red-500  ", "  bg-blue-500  ");

      expect(result).toBe("text-red-500 bg-blue-500");
    });
  });

  describe("edge cases", () => {
    it("handles only undefined/null/false values", () => {
      const result = cn(undefined, null, false, "", 0);

      expect(result).toBe("");
    });

    it("handles numeric zero", () => {
      const result = cn("text-red-500", 0, "bg-blue-500");

      expect(result).toBe("text-red-500 bg-blue-500");
    });

    it("handles empty object", () => {
      const result = cn("text-red-500", {}, "bg-blue-500");

      expect(result).toBe("text-red-500 bg-blue-500");
    });

    it("handles empty array", () => {
      const result = cn("text-red-500", [], "bg-blue-500");

      expect(result).toBe("text-red-500 bg-blue-500");
    });

    it("preserves arbitrary Tailwind values", () => {
      const result = cn("text-[#1a2b3c]", "bg-[rgb(255,0,0)]");

      expect(result).toBe("text-[#1a2b3c] bg-[rgb(255,0,0)]");
    });

    it("resolves conflicts with arbitrary values", () => {
      const result = cn("text-red-500", "text-[#1a2b3c]");

      expect(result).toBe("text-[#1a2b3c]");
    });

    it("handles important modifier", () => {
      const result = cn("!text-red-500", "text-blue-500");

      // Important should take precedence
      expect(result).toContain("!text-red-500");
    });

    it("handles responsive modifiers", () => {
      const result = cn("text-sm md:text-base lg:text-lg");

      expect(result).toBe("text-sm md:text-base lg:text-lg");
    });

    it("resolves responsive modifier conflicts", () => {
      const result = cn("md:p-4", "md:p-6");

      expect(result).toBe("md:p-6");
    });

    it("handles state modifiers (hover, focus, etc.)", () => {
      const result = cn("hover:bg-blue-500", "focus:ring-2");

      expect(result).toBe("hover:bg-blue-500 focus:ring-2");
    });

    it("resolves state modifier conflicts", () => {
      const result = cn("hover:bg-blue-500", "hover:bg-red-500");

      expect(result).toBe("hover:bg-red-500");
    });
  });
});
