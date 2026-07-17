import { useMemo } from "react";
import { Line } from "react-chartjs-2";
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Tooltip,
} from "chart.js";

ChartJS.register(CategoryScale, LinearScale, PointElement, LineElement, Tooltip);

const WINDOW = 20; // ~60s of history at one chunk every 3s

export default function EmotionTimeline({ timeline = [] }) {
  const points = timeline.slice(-WINDOW);

  const data = useMemo(
    () => ({
      labels: points.map((_, i) => i),
      datasets: [
        {
          data: points.map((p) => p.safety_score),
          borderColor: "#6366f1",
          backgroundColor: "#6366f1",
          borderWidth: 2,
          tension: 0.3,
          pointRadius: points.map((p) => (p.alert_triggered ? 5 : 2)),
          pointBackgroundColor: points.map((p) => (p.alert_triggered ? "#ef4444" : "#818cf8")),
        },
      ],
    }),
    [points],
  );

  const options = {
    responsive: true,
    maintainAspectRatio: false,
    animation: { duration: 250 },
    scales: {
      y: { min: 0, max: 100, ticks: { color: "#6b7280" }, grid: { color: "#1f2937" } },
      x: { display: false },
    },
    plugins: { legend: { display: false }, tooltip: { enabled: true } },
  };

  return (
    <div className="bg-gray-900 border border-gray-800 hover:border-gray-700/80 transition-colors rounded-2xl p-5">
      <div className="text-xs text-gray-500 uppercase tracking-wide mb-3">
        Emotion timeline · last {points.length * 3}s
      </div>
      <div className="relative h-48">
        {/* Colour bands matching the risk thresholds: green 80-100, amber 50-80, red 0-50 */}
        <div className="absolute inset-0 flex flex-col rounded-lg overflow-hidden pointer-events-none opacity-10">
          <div style={{ height: "20%" }} className="bg-green-500" />
          <div style={{ height: "30%" }} className="bg-yellow-500" />
          <div style={{ height: "50%" }} className="bg-red-500" />
        </div>
        {points.length > 0 ? (
          <Line data={data} options={options} />
        ) : (
          <div className="h-full flex items-center justify-center text-gray-600 text-sm">
            Start monitoring to see the timeline
          </div>
        )}
      </div>
    </div>
  );
}
