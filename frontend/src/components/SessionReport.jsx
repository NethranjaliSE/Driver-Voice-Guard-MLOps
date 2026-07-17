import { AnimatePresence, motion } from "framer-motion";
import { X, Download } from "lucide-react";
import toast from "react-hot-toast";
import { downloadReportPdf } from "../api";

const VERDICT_COLORS = {
  "SAFE TO DRIVE": "text-green-400",
  "TAKE A BREAK": "text-yellow-400",
  "STOP NOW": "text-red-400",
  "NO DATA": "text-gray-400",
};

export default function SessionReport({ report, onClose }) {
  async function exportPdf() {
    try {
      await downloadReportPdf(report.session_id);
    } catch (err) {
      toast.error(err.message || "Could not generate PDF");
    }
  }

  return (
    <AnimatePresence>
      {report && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          className="fixed inset-0 bg-black/70 backdrop-blur-sm flex items-center justify-center z-50 p-4"
        >
          <motion.div
            initial={{ opacity: 0, scale: 0.95, y: 12 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.95 }}
            className="bg-gray-900 border border-gray-800 rounded-2xl p-6 max-w-md w-full space-y-4"
          >
            <div className="flex items-center justify-between">
              <h2 className="text-lg font-semibold">Session Report</h2>
              <button onClick={onClose} className="text-gray-500 hover:text-gray-300">
                <X size={20} />
              </button>
            </div>

            <div className={`text-2xl font-bold ${VERDICT_COLORS[report.overall_verdict] || "text-gray-300"}`}>
              {report.overall_verdict}
            </div>

            <div className="grid grid-cols-2 gap-3 text-sm">
              <div className="bg-gray-800/50 rounded-xl p-3">
                <div className="text-gray-500 text-xs">Duration</div>
                <div className="font-medium">{report.duration_seconds}s</div>
              </div>
              <div className="bg-gray-800/50 rounded-xl p-3">
                <div className="text-gray-500 text-xs">Avg. safety score</div>
                <div className="font-medium">{report.average_safety_score}</div>
              </div>
              <div className="bg-gray-800/50 rounded-xl p-3">
                <div className="text-gray-500 text-xs">Dominant state</div>
                <div className="font-medium capitalize">{report.dominant_state}</div>
              </div>
              <div className="bg-gray-800/50 rounded-xl p-3">
                <div className="text-gray-500 text-xs">Risk events</div>
                <div className="font-medium">{report.risk_events.length}</div>
              </div>
            </div>

            <button
              onClick={exportPdf}
              className="w-full flex items-center justify-center gap-2 px-4 py-3 bg-indigo-600 hover:bg-indigo-500 text-white rounded-xl font-medium transition-colors"
            >
              <Download size={16} /> Export PDF
            </button>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
