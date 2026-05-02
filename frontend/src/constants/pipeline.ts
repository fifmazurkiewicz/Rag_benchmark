export const GRAPH_PIPELINE_TYPES = new Set(["falkordb_graphrag", "neo4j_graphrag"]);

export const STATUS_COLORS: Record<string, string> = {
  pending: "text-gray-400",
  running: "text-yellow-400",
  done: "text-green-400",
  error: "text-red-400",
};
