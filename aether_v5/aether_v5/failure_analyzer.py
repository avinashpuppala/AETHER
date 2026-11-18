"""Summarize falsification outcomes without hiding failed candidates."""
class FailureAnalyzer:
    def analyze(self, candidate_reports):
        failed = []
        passed = []
        for report in candidate_reports:
            if report.get("verified"):
                passed.append(report.get("candidate"))
            else:
                failed.append({
                    "candidate": report.get("candidate"),
                    "counterexample_count": len(report.get("counterexamples", [])),
                    "first_counterexample": (report.get("counterexamples") or [None])[0],
                })
        return {
            "candidates_tested": len(candidate_reports),
            "verified_candidates": passed,
            "rejected_candidates": failed,
            "rejection_rate": len(failed) / max(1, len(candidate_reports)),
        }
