import type { ProblemResponse, ReadDocumentsApiV1DocumentsGetOperation } from "@contracts";
import { describe, expect, it } from "vitest";

describe("generated contracts", () => {
  it("can be imported from packages/contracts/typescript", () => {
    const problem: ProblemResponse = {
      detail: "Example",
      instance: "/api/v1/example",
      status: 400,
      title: "Bad request",
      type: "https://ragdoll.dev/problems/example"
    };
    const query: ReadDocumentsApiV1DocumentsGetOperation["queryParams"] = {
      all_spaces: true,
      page: 1,
      page_size: 20
    };

    expect(problem.status).toBe(400);
    expect(query.page_size).toBe(20);
  });
});
