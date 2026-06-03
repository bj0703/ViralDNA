from __future__ import annotations

import html
import json

from backend.app.models.sample_analysis import SessionJob


def render_job_html(job: SessionJob) -> str:
    cards = []
    for sample in job.sample_results:
        middle_items = "".join(
            f"<li>{segment['label']} ({segment['start_seconds']}s - {segment['end_seconds']}s): {html.escape(segment['summary'])}</li>"
            for segment in sample.script_structure["middle_segments"]
        )
        pace_items = "".join(
            f"<li>{segment['label']} | 节奏: {segment['pace']} | 镜头密度估计: {segment['shot_density_estimate']}</li>"
            for segment in sample.pace_structure["segments"]
        )
        warnings = "".join(f"<li>{html.escape(message)}</li>" for message in sample.warnings) or "<li>无</li>"
        transcript = sample.metadata.transcript_overview or "未提供"
        cards.append(
            f"""
            <section class="card">
              <h2>{html.escape(sample.metadata.original_filename)}</h2>
              <p><strong>时长:</strong> {sample.metadata.duration_seconds}s {'(估计)' if sample.metadata.duration_is_estimated else ''}</p>
              <p><strong>语音概览:</strong> {html.escape(transcript)}</p>
              <p><strong>预览链接:</strong> <a href="{html.escape(sample.metadata.preview_url or '#')}">打开文件</a></p>
              <h3>脚本结构</h3>
              <p><strong>Hook:</strong> {html.escape(sample.script_structure['hook']['summary'])}</p>
              <ul>{middle_items}</ul>
              <p><strong>结尾:</strong> {html.escape(sample.script_structure['ending']['summary'])}</p>
              <h3>节奏结构</h3>
              <p><strong>整体节奏:</strong> {html.escape(sample.pace_structure['overall_pace'])}</p>
              <p><strong>高潮位置:</strong> {sample.pace_structure['highlight_position_seconds']}s</p>
              <ul>{pace_items}</ul>
              <h3>告警与兜底</h3>
              <ul>{warnings}</ul>
              <details>
                <summary>机器可读结果</summary>
                <pre>{html.escape(json.dumps(sample.to_dict(), ensure_ascii=False, indent=2))}</pre>
              </details>
            </section>
            """
        )

    return f"""
    <!doctype html>
    <html lang="zh-CN">
      <head>
        <meta charset="utf-8" />
        <title>样例分析结果</title>
        <style>
          :root {{
            color-scheme: light;
            --bg: #f6f2e9;
            --card: #fffaf2;
            --border: #d4c5ae;
            --text: #2f2418;
            --accent: #8f4b2a;
          }}
          body {{
            margin: 0;
            font-family: "Microsoft YaHei", "Segoe UI", sans-serif;
            background: radial-gradient(circle at top, #fff9ef 0%, var(--bg) 60%);
            color: var(--text);
          }}
          main {{
            max-width: 1080px;
            margin: 0 auto;
            padding: 32px 20px 48px;
          }}
          .hero {{
            margin-bottom: 24px;
            padding: 20px 24px;
            border: 1px solid var(--border);
            border-radius: 18px;
            background: linear-gradient(135deg, #fffef9, #f2e7d3);
          }}
          .grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
            gap: 16px;
          }}
          .card {{
            padding: 18px;
            border: 1px solid var(--border);
            border-radius: 18px;
            background: var(--card);
            box-shadow: 0 10px 30px rgba(84, 48, 24, 0.08);
          }}
          h1, h2, h3 {{
            margin-top: 0;
          }}
          a {{
            color: var(--accent);
          }}
          pre {{
            white-space: pre-wrap;
            word-break: break-word;
            font-size: 12px;
            background: #f8f3e9;
            padding: 12px;
            border-radius: 12px;
          }}
        </style>
      </head>
      <body>
        <main>
          <section class="hero">
            <h1>样例分析结果</h1>
            <p>任务 ID: {html.escape(job.job_id)}</p>
            <p>会话模式: {html.escape(job.debug.get('session_mode', 'unknown'))}</p>
            <p>样例数量: {job.debug.get('sample_count', 0)}</p>
          </section>
          <section class="grid">
            {''.join(cards)}
          </section>
        </main>
      </body>
    </html>
    """
