import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid
} from "recharts";

export default function StrategyChart({ data }) {
  if (!data || !data.results) return null;

  const chartData = data.results.map((s) => ({
    name: s.name || "Unknown",
    score: Number((s.score || 0).toFixed(2)),
    confidence: Number((s.confidence || 0).toFixed(2))
  }));

  return (
    <div style={{ marginTop: "30px" }}>
      <h3>📊 Strategy Performance</h3>

      <BarChart width={500} height={300} data={chartData}>
        <CartesianGrid strokeDasharray="3 3" />
        <XAxis dataKey="name" />
        <YAxis />
        <Tooltip />
        <Bar dataKey="score" />
        <Bar dataKey="confidence" />
      </BarChart>
    </div>
  );
}