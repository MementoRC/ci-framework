"""Artifact management for GitHub Actions workflow integration."""

import json
from datetime import datetime
from pathlib import Path
from typing import Any


class ArtifactManager:
    """Manages creation and organization of workflow artifacts."""

    def __init__(self, artifact_path: str | Path = "./artifacts"):
        """Initialize artifact manager.

        Args:
            artifact_path: Base directory for storing artifacts.
        """
        self.artifact_path = Path(artifact_path)
        self.artifact_path.mkdir(parents=True, exist_ok=True)

        # Create subdirectories for different artifact types
        self.reports_path = self.artifact_path / "reports"
        self.logs_path = self.artifact_path / "logs"
        self.data_path = self.artifact_path / "data"

        for path in [self.reports_path, self.logs_path, self.data_path]:
            path.mkdir(exist_ok=True)

    def create_artifact(
        self, name: str, content: str | dict | list, content_type: str = "text/plain"
    ) -> Path | None:
        """Create an artifact file.

        Args:
            name: Artifact filename.
            content: Content to store.
            content_type: MIME type of content.

        Returns:
            Path to created artifact or None if failed.
        """
        try:
            # Determine file path based on content type
            file_path = self._get_artifact_path(name, content_type)

            # Write content based on type
            if content_type == "application/json" or isinstance(content, dict | list):
                with open(file_path, "w", encoding="utf-8") as f:
                    json.dump(content, f, indent=2, default=str)
            else:
                # Text content
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(str(content))

            return file_path

        except Exception as e:
            print(f"Error creating artifact {name}: {e}")
            return None

    def create_report_artifact(
        self, report_name: str, report_data: dict[str, Any], format_type: str = "json"
    ) -> Path | None:
        """Create a structured report artifact.

        Args:
            report_name: Name of the report.
            report_data: Report data.
            format_type: Output format (json, html, markdown).

        Returns:
            Path to created report artifact.
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{report_name}_{timestamp}.{format_type}"

        if format_type == "json":
            return self.create_artifact(filename, report_data, "application/json")
        elif format_type == "html":
            html_content = self._generate_html_report(report_name, report_data)
            return self.create_artifact(filename, html_content, "text/html")
        elif format_type == "markdown":
            md_content = self._generate_markdown_report(report_name, report_data)
            return self.create_artifact(filename, md_content, "text/markdown")
        else:
            raise ValueError(f"Unsupported format type: {format_type}")

    def create_log_artifact(
        self, log_name: str, log_content: str, log_level: str = "info"
    ) -> Path | None:
        """Create a log artifact.

        Args:
            log_name: Name of the log.
            log_content: Log content.
            log_level: Log level (debug, info, warning, error).

        Returns:
            Path to created log artifact.
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{log_name}_{log_level}_{timestamp}.log"

        # Add timestamp to log content
        timestamped_content = f"[{datetime.now().isoformat()}] {log_content}\n"

        log_path = self.logs_path / filename
        try:
            with open(log_path, "a", encoding="utf-8") as f:
                f.write(timestamped_content)
            return log_path
        except Exception as e:
            print(f"Error creating log artifact {log_name}: {e}")
            return None

    def create_data_artifact(
        self, data_name: str, data: dict | list | str, format_type: str = "json"
    ) -> Path | None:
        """Create a data artifact.

        Args:
            data_name: Name of the data file.
            data: Data to store.
            format_type: Format (json, csv, txt).

        Returns:
            Path to created data artifact.
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{data_name}_{timestamp}.{format_type}"

        data_path = self.data_path / filename

        try:
            if format_type == "json":
                with open(data_path, "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=2, default=str)
            elif format_type == "csv":
                # Simple CSV generation for dict/list data
                csv_content = data if isinstance(data, str) else self._generate_csv(data)
                with open(data_path, "w", encoding="utf-8") as f:
                    f.write(csv_content)
            else:
                # Text format
                with open(data_path, "w", encoding="utf-8") as f:
                    f.write(str(data))

            return data_path

        except Exception as e:
            print(f"Error creating data artifact {data_name}: {e}")
            return None

    def list_artifacts(self, artifact_type: str | None = None) -> list[dict[str, Any]]:
        """List all artifacts.

        Args:
            artifact_type: Filter by type (reports, logs, data).

        Returns:
            List of artifact information.
        """
        artifacts = []

        search_paths = []
        if artifact_type == "reports":
            search_paths = [self.reports_path]
        elif artifact_type == "logs":
            search_paths = [self.logs_path]
        elif artifact_type == "data":
            search_paths = [self.data_path]
        else:
            search_paths = [self.reports_path, self.logs_path, self.data_path]

        for search_path in search_paths:
            for file_path in search_path.glob("*"):
                if file_path.is_file():
                    stat = file_path.stat()
                    artifacts.append(
                        {
                            "name": file_path.name,
                            "path": str(file_path),
                            "type": search_path.name,
                            "size": stat.st_size,
                            "created": datetime.fromtimestamp(stat.st_ctime).isoformat(),
                            "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                        }
                    )

        # Sort by creation time, newest first
        artifacts.sort(key=lambda x: str(x["created"]), reverse=True)
        return artifacts

    def get_artifact_summary(self) -> dict[str, Any]:
        """Get summary of all artifacts.

        Returns:
            Summary information about artifacts.
        """
        artifacts = self.list_artifacts()

        summary = {
            "total_count": len(artifacts),
            "total_size": sum(a["size"] for a in artifacts),
            "by_type": {},
            "recent_artifacts": artifacts[:5],  # 5 most recent
        }

        # Group by type
        for artifact in artifacts:
            artifact_type = artifact["type"]
            if artifact_type not in summary["by_type"]:
                summary["by_type"][artifact_type] = {"count": 0, "size": 0}

            summary["by_type"][artifact_type]["count"] += 1
            summary["by_type"][artifact_type]["size"] += artifact["size"]

        return summary

    def cleanup_old_artifacts(self, max_age_days: int = 7) -> int:
        """Clean up old artifacts.

        Args:
            max_age_days: Maximum age of artifacts to keep.

        Returns:
            Number of artifacts cleaned up.
        """
        cutoff_time = datetime.now().timestamp() - (max_age_days * 24 * 60 * 60)
        cleaned_count = 0

        for search_path in [self.reports_path, self.logs_path, self.data_path]:
            for file_path in search_path.glob("*"):
                if file_path.is_file() and file_path.stat().st_ctime < cutoff_time:
                    try:
                        file_path.unlink()
                        cleaned_count += 1
                    except Exception as e:
                        print(f"Warning: Failed to delete {file_path}: {e}")

        return cleaned_count

    def _get_artifact_path(self, name: str, content_type: str) -> Path:
        """Determine appropriate path for artifact based on content type."""
        if content_type in ["application/json", "text/html", "text/markdown"]:
            return self.reports_path / name
        elif content_type == "text/plain" and name.endswith(".log"):
            return self.logs_path / name
        elif content_type in ["text/csv", "application/csv"]:
            return self.data_path / name
        elif content_type == "text/plain":
            # Put text files in data directory for listing
            return self.data_path / name
        else:
            return self.artifact_path / name

    def _generate_html_report(self, report_name: str, report_data: dict[str, Any]) -> str:
        """Generate HTML report from data."""
        html = f"""<!DOCTYPE html>
<html>
<head>
    <title>{report_name} Report</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        .header {{ background-color: #f5f5f5; padding: 15px; border-radius: 5px; }}
        .section {{ margin: 20px 0; }}
        .data {{ background-color: #f9f9f9; padding: 10px; border-radius: 3px; }}
        table {{ border-collapse: collapse; width: 100%; }}
        th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
        th {{ background-color: #f2f2f2; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>{report_name} Report</h1>
        <p>Generated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</p>
    </div>

    <div class="section">
        <h2>Report Data</h2>
        <div class="data">
            <pre>{json.dumps(report_data, indent=2)}</pre>
        </div>
    </div>
</body>
</html>"""
        return html

    def _generate_markdown_report(self, report_name: str, report_data: dict[str, Any]) -> str:
        """Generate Markdown report from data."""
        markdown = f"""# {report_name} Report

Generated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

## Report Data

```json
{json.dumps(report_data, indent=2)}
```
"""
        return markdown

    def _generate_csv(self, data: dict | list) -> str:
        """Generate simple CSV from data."""
        if isinstance(data, list) and len(data) > 0 and isinstance(data[0], dict):
            # List of dictionaries
            if not data:
                return ""

            headers = list(data[0].keys())
            csv_lines = [",".join(headers)]

            for row in data:
                values = [str(row.get(header, "")) for header in headers]
                csv_lines.append(",".join(f'"{v}"' for v in values))

            return "\n".join(csv_lines)

        elif isinstance(data, dict):
            # Single dictionary
            headers = ["Key", "Value"]
            csv_lines = [",".join(headers)]

            for key, value in data.items():
                csv_lines.append(f'"{key}","{value}"')

            return "\n".join(csv_lines)

        else:
            # Convert to string
            return str(data)
