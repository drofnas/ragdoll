import type {
  ReadSearchResultsApiV1SearchGetOperation,
  SearchResponse
} from "@contracts";

import { apiClient } from "../../../shared/api/client";

export type SearchQuery = ReadSearchResultsApiV1SearchGetOperation["queryParams"];

export function readSearchResults(query: SearchQuery) {
  return apiClient.getJson<SearchResponse>("/api/v1/search", { query });
}
