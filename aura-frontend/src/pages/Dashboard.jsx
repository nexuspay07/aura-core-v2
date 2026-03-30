import React, { useEffect, useState } from "react";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
  ScatterChart,
  Scatter
} from "recharts";

export default function Dashboard() {
  const [data, setData] = useState([]);
  const [scatter, setScatter] = useState([]);

  const fetchData = async () => {
    const token = localStorage.getItem("token");

    const res = await fetch("http://aura-ai.onrender.com/strategy/all", {
      headers: {
        Authorization: `Bearer ${token}`,
      },
    });

    const strategies = await res.json();

    // 📈 Line chart data (scores)
    const chartData = strategies.map((s, index) => ({
      name: s.name + "-" + index,
      score: s.score,
      votes: s.votes
    }));

    // 🎯 Scatter data (risk vs score)
    const scatterData = strategies.map((s) => ({
      x: s.data?.risk === "high" ? 3 : s.data?.risk === "medium" ? 2 : 1,
      y: s.score,
      name: s.name
    }));

    setData(chartData);
    setScatter(scatterData);
  };

  useEffect(() => {
    fetchData();
  }, []);

  return (
    <div style={{ padding: "20px", color: "white", background: "#0f172a", minHeight: "100vh" }}>
      <h1>AURA Dashboard 📊</h1>

      {/* ========================= */}
      {/* 📈 STRATEGY PERFORMANCE */}
      {/* ========================= */}
      <h2>Strategy Performance</h2>

      <LineChart width={600} height={300} data={data}>
        <CartesianGrid stroke="#444" />
        <XAxis dataKey="name" />
        <YAxis />
        <Tooltip />
        <Line type="monotone" dataKey="score" stroke="#38bdf8" />
      </LineChart>

      {/* ========================= */}
      {/* 🎯 RISK VS SCORE */}
      {/* ========================= */}
      <h2>Risk vs Score</h2>

      <ScatterChart width={600} height={300}>
        <CartesianGrid />
        <XAxis dataKey="x" name="Risk Level" />
        <YAxis dataKey="y" name="Score" />
        <Tooltip cursor={{ strokeDasharray: "3 3" }} />
        <Scatter data={scatter} fill="#22c55e" />
      </ScatterChart>

    </div>
  );
}