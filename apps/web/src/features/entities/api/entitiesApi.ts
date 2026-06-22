import type {
  EntityDetailResponse,
  EntityListResponse,
  GraphResponse,
  ReadEntitiesApiV1EntitiesGetOperation,
  ReadEntityDetailApiV1EntitiesEntityIdGetOperation,
  ReadEntitySubgraphApiV1KnowledgeGraphEntitiesEntityIdSubgraphGetOperation
} from "@contracts";

import { apiClient } from "../../../shared/api/client";

export type ListEntitiesQuery = ReadEntitiesApiV1EntitiesGetOperation["queryParams"];
export type EntityPathParams = ReadEntityDetailApiV1EntitiesEntityIdGetOperation["pathParams"];
export type EntityDetailQuery = ReadEntityDetailApiV1EntitiesEntityIdGetOperation["queryParams"];
export type EntitySubgraphQuery = ReadEntitySubgraphApiV1KnowledgeGraphEntitiesEntityIdSubgraphGetOperation["queryParams"];

export function listEntities(query: ListEntitiesQuery) {
  return apiClient.getJson<EntityListResponse>("/api/v1/entities", { query });
}

export function readEntity(entityId: EntityPathParams["entity_id"], query: EntityDetailQuery) {
  return apiClient.getJson<EntityDetailResponse>(`/api/v1/entities/${entityId}`, { query });
}

export function readEntitySubgraph(
  entityId: EntityPathParams["entity_id"],
  query: EntitySubgraphQuery
) {
  return apiClient.getJson<GraphResponse>(
    `/api/v1/knowledge-graph/entities/${entityId}/subgraph`,
    { query }
  );
}
