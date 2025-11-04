"""
CrawlAgent - Custom Dark Theme
Created: 2025-11-04

전문적인 다크 테마 + 커스텀 CSS
참고: Grafana, Datadog, Kibana 스타일
"""

import gradio as gr
from gradio.themes.base import Base
from gradio.themes.utils import colors, fonts, sizes


class CrawlAgentDarkTheme(Base):
    """CrawlAgent 전용 다크 테마"""

    def __init__(
        self,
        *,
        primary_hue: colors.Color | str = colors.purple,
        secondary_hue: colors.Color | str = colors.gray,
        neutral_hue: colors.Color | str = colors.gray,
        spacing_size: sizes.Size | str = sizes.spacing_md,
        radius_size: sizes.Size | str = sizes.radius_md,
        text_size: sizes.Size | str = sizes.text_md,
        font: fonts.Font | str | tuple = fonts.GoogleFont("Inter"),
        font_mono: fonts.Font | str | tuple = fonts.GoogleFont("JetBrains Mono"),
    ):
        super().__init__(
            primary_hue=primary_hue,
            secondary_hue=secondary_hue,
            neutral_hue=neutral_hue,
            spacing_size=spacing_size,
            radius_size=radius_size,
            text_size=text_size,
            font=font,
            font_mono=font_mono,
        )

        # 다크 모드 색상 오버라이드
        self.set(
            # 배경
            body_background_fill="#1a1b1e",
            body_background_fill_dark="#1a1b1e",
            background_fill_primary="#1a1b1e",
            background_fill_primary_dark="#1a1b1e",
            background_fill_secondary="#2d2e32",
            background_fill_secondary_dark="#2d2e32",

            # 카드/컨테이너
            block_background_fill="#2d2e32",
            block_background_fill_dark="#2d2e32",
            block_border_color="#4a4b4f",
            block_border_color_dark="#4a4b4f",

            # 텍스트
            body_text_color="#e5e7eb",
            body_text_color_dark="#e5e7eb",
            body_text_color_subdued="#9ca3af",
            body_text_color_subdued_dark="#9ca3af",

            # 버튼 - Primary
            button_primary_background_fill="#667eea",
            button_primary_background_fill_dark="#667eea",
            button_primary_background_fill_hover="#5568d3",
            button_primary_background_fill_hover_dark="#5568d3",
            button_primary_text_color="#ffffff",
            button_primary_text_color_dark="#ffffff",
            button_primary_border_color="#667eea",
            button_primary_border_color_dark="#667eea",

            # 버튼 - Secondary
            button_secondary_background_fill="#3a3b3f",
            button_secondary_background_fill_dark="#3a3b3f",
            button_secondary_background_fill_hover="#4a4b4f",
            button_secondary_background_fill_hover_dark="#4a4b4f",
            button_secondary_text_color="#e5e7eb",
            button_secondary_text_color_dark="#e5e7eb",
            button_secondary_border_color="#4a4b4f",
            button_secondary_border_color_dark="#4a4b4f",

            # 입력 필드
            input_background_fill="#3a3b3f",
            input_background_fill_dark="#3a3b3f",
            input_background_fill_focus="#4a4b4f",
            input_background_fill_focus_dark="#4a4b4f",
            input_border_color="#4a4b4f",
            input_border_color_dark="#4a4b4f",
            input_border_color_focus="#667eea",
            input_border_color_focus_dark="#667eea",

            # 경계선
            border_color_primary="#4a4b4f",
            border_color_primary_dark="#4a4b4f",
            border_color_accent="#667eea",
            border_color_accent_dark="#667eea",

            # 링크
            link_text_color="#667eea",
            link_text_color_dark="#667eea",
            link_text_color_hover="#5568d3",
            link_text_color_hover_dark="#5568d3",

            # Shadow
            shadow_drop="0 4px 6px rgba(0,0,0,0.3)",
            shadow_drop_lg="0 10px 15px rgba(0,0,0,0.4)",
        )


def get_custom_css():
    """추가 커스텀 CSS"""
    return """
    /* ============================================ */
    /* 전역 스타일 */
    /* ============================================ */

    * {
        font-family: 'Inter', sans-serif !important;
    }

    .gradio-container {
        max-width: 1600px !important;
        margin: 0 auto !important;
        padding: 20px !important;
    }

    /* ============================================ */
    /* 탭 스타일 */
    /* ============================================ */

    .tab-nav {
        border-bottom: 2px solid #4a4b4f !important;
        padding-bottom: 0 !important;
        margin-bottom: 30px !important;
    }

    .tab-nav button {
        font-size: 1.1rem !important;
        font-weight: 600 !important;
        padding: 12px 28px !important;
        margin: 0 4px !important;
        border-radius: 8px 8px 0 0 !important;
        border: none !important;
        background: transparent !important;
        color: #9ca3af !important;
        transition: all 0.3s ease !important;
    }

    .tab-nav button:hover {
        background: #3a3b3f !important;
        color: #e5e7eb !important;
    }

    .tab-nav button[aria-selected="true"] {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%) !important;
        color: white !important;
        box-shadow: 0 4px 12px rgba(102, 126, 234, 0.4) !important;
    }

    /* ============================================ */
    /* 카드 스타일 */
    /* ============================================ */

    .card {
        background: #2d2e32 !important;
        border: 1px solid #4a4b4f !important;
        border-radius: 12px !important;
        padding: 24px !important;
        box-shadow: 0 4px 6px rgba(0,0,0,0.2) !important;
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1) !important;
    }

    .card:hover {
        transform: translateY(-2px) !important;
        box-shadow: 0 8px 16px rgba(0,0,0,0.3) !important;
        border-color: #667eea50 !important;
    }

    .interactive-card {
        cursor: pointer !important;
    }

    .interactive-card:hover {
        transform: translateY(-4px) scale(1.02) !important;
        box-shadow: 0 12px 24px rgba(102, 126, 234, 0.3) !important;
    }

    /* ============================================ */
    /* 상태 박스 (성공/경고/오류) */
    /* ============================================ */

    .status-box {
        padding: 24px !important;
        border-radius: 12px !important;
        margin: 20px 0 !important;
        animation: fadeIn 0.5s ease-in !important;
    }

    .status-success {
        background: linear-gradient(135deg, #10b98120 0%, #10b98130 100%) !important;
        border-left: 4px solid #10b981 !important;
        color: #10b981 !important;
    }

    .status-warning {
        background: linear-gradient(135deg, #f59e0b20 0%, #f59e0b30 100%) !important;
        border-left: 4px solid #f59e0b !important;
        color: #f59e0b !important;
    }

    .status-error {
        background: linear-gradient(135deg, #ef444420 0%, #ef444430 100%) !important;
        border-left: 4px solid #ef4444 !important;
        color: #ef4444 !important;
    }

    .status-info {
        background: linear-gradient(135deg, #3b82f620 0%, #3b82f630 100%) !important;
        border-left: 4px solid #3b82f6 !important;
        color: #3b82f6 !important;
    }

    /* ============================================ */
    /* 버튼 스타일 */
    /* ============================================ */

    button {
        font-weight: 600 !important;
        transition: all 0.3s ease !important;
        cursor: pointer !important;
    }

    button:hover {
        transform: translateY(-2px) !important;
        box-shadow: 0 6px 12px rgba(0,0,0,0.3) !important;
    }

    button:active {
        transform: translateY(0) !important;
        box-shadow: 0 2px 4px rgba(0,0,0,0.2) !important;
    }

    button[variant="primary"] {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%) !important;
        box-shadow: 0 4px 12px rgba(102, 126, 234, 0.4) !important;
    }

    button[variant="primary"]:hover {
        box-shadow: 0 8px 20px rgba(102, 126, 234, 0.5) !important;
    }

    button[variant="stop"] {
        background: linear-gradient(135deg, #ef4444 0%, #dc2626 100%) !important;
    }

    /* ============================================ */
    /* 입력 필드 */
    /* ============================================ */

    input, textarea, select {
        background: #3a3b3f !important;
        border: 1px solid #4a4b4f !important;
        color: #e5e7eb !important;
        border-radius: 8px !important;
        transition: all 0.3s ease !important;
    }

    input:focus, textarea:focus, select:focus {
        border-color: #667eea !important;
        box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.2) !important;
        outline: none !important;
    }

    input::placeholder, textarea::placeholder {
        color: #6b7280 !important;
    }

    /* ============================================ */
    /* 데이터 테이블 */
    /* ============================================ */

    .dataframe {
        background: #2d2e32 !important;
        border: 1px solid #4a4b4f !important;
        border-radius: 8px !important;
        overflow: hidden !important;
    }

    .dataframe thead {
        background: #3a3b3f !important;
    }

    .dataframe th {
        background: #3a3b3f !important;
        color: #e5e7eb !important;
        font-weight: 600 !important;
        padding: 12px !important;
        border-bottom: 2px solid #4a4b4f !important;
    }

    .dataframe td {
        color: #e5e7eb !important;
        padding: 12px !important;
        border-bottom: 1px solid #4a4b4f !important;
    }

    .dataframe tr:hover {
        background: #3a3b3f !important;
    }

    .dataframe tr:last-child td {
        border-bottom: none !important;
    }

    /* ============================================ */
    /* 로딩 애니메이션 */
    /* ============================================ */

    .loading-overlay {
        position: fixed;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        background: rgba(26, 27, 30, 0.95);
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        z-index: 9999;
    }

    .loading-spinner {
        border: 6px solid #4a4b4f;
        border-top: 6px solid #667eea;
        border-radius: 50%;
        width: 60px;
        height: 60px;
        animation: spin 1s linear infinite;
    }

    .loading-text {
        color: #e5e7eb;
        margin-top: 20px;
        font-size: 1.2em;
        animation: pulse 1.5s ease-in-out infinite;
    }

    @keyframes spin {
        0% { transform: rotate(0deg); }
        100% { transform: rotate(360deg); }
    }

    @keyframes pulse {
        0%, 100% { opacity: 1; }
        50% { opacity: 0.5; }
    }

    /* ============================================ */
    /* 성공 체크마크 애니메이션 */
    /* ============================================ */

    .success-checkmark {
        display: inline-block;
        animation: checkmark 0.5s ease-in-out;
    }

    @keyframes checkmark {
        0% {
            transform: scale(0) rotate(0deg);
            opacity: 0;
        }
        50% {
            transform: scale(1.2) rotate(180deg);
        }
        100% {
            transform: scale(1) rotate(360deg);
            opacity: 1;
        }
    }

    /* ============================================ */
    /* Fade In 애니메이션 */
    /* ============================================ */

    @keyframes fadeIn {
        from {
            opacity: 0;
            transform: translateY(20px);
        }
        to {
            opacity: 1;
            transform: translateY(0);
        }
    }

    /* ============================================ */
    /* 진행 바 */
    /* ============================================ */

    .progress-bar {
        width: 100%;
        height: 8px;
        background: #3a3b3f;
        border-radius: 4px;
        overflow: hidden;
        margin: 10px 0;
    }

    .progress-fill {
        height: 100%;
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
        transition: width 0.3s ease;
        animation: shimmer 2s linear infinite;
    }

    @keyframes shimmer {
        0% { background-position: -1000px 0; }
        100% { background-position: 1000px 0; }
    }

    /* ============================================ */
    /* 툴팁 */
    /* ============================================ */

    .tooltip {
        position: relative;
        display: inline-block;
        cursor: help;
    }

    .tooltip:hover::after {
        content: attr(data-tooltip);
        position: absolute;
        bottom: 125%;
        left: 50%;
        transform: translateX(-50%);
        background: #2d2e32;
        color: #e5e7eb;
        padding: 8px 12px;
        border-radius: 6px;
        white-space: nowrap;
        font-size: 0.9em;
        border: 1px solid #4a4b4f;
        box-shadow: 0 4px 12px rgba(0,0,0,0.3);
        z-index: 1000;
        animation: fadeIn 0.3s ease-in;
    }

    /* ============================================ */
    /* 배지 */
    /* ============================================ */

    .badge {
        display: inline-block;
        padding: 4px 12px;
        border-radius: 12px;
        font-size: 0.85em;
        font-weight: 600;
        margin: 0 4px;
    }

    .badge-success {
        background: #10b98130;
        color: #10b981;
        border: 1px solid #10b981;
    }

    .badge-warning {
        background: #f59e0b30;
        color: #f59e0b;
        border: 1px solid #f59e0b;
    }

    .badge-error {
        background: #ef444430;
        color: #ef4444;
        border: 1px solid #ef4444;
    }

    .badge-info {
        background: #3b82f630;
        color: #3b82f6;
        border: 1px solid #3b82f6;
    }

    /* ============================================ */
    /* 반응형 디자인 */
    /* ============================================ */

    @media (max-width: 1200px) {
        .gradio-container {
            max-width: 100% !important;
            padding: 16px !important;
        }
    }

    @media (max-width: 768px) {
        .gradio-container {
            padding: 12px !important;
        }

        .card {
            padding: 16px !important;
        }

        .tab-nav button {
            font-size: 0.95rem !important;
            padding: 10px 16px !important;
        }

        button {
            font-size: 0.9rem !important;
            padding: 8px 16px !important;
        }
    }

    @media (max-width: 480px) {
        .tab-nav {
            flex-wrap: wrap !important;
        }

        .tab-nav button {
            flex: 1 1 45% !important;
            margin: 2px !important;
        }
    }

    /* ============================================ */
    /* 스크롤바 */
    /* ============================================ */

    ::-webkit-scrollbar {
        width: 12px;
        height: 12px;
    }

    ::-webkit-scrollbar-track {
        background: #2d2e32;
        border-radius: 6px;
    }

    ::-webkit-scrollbar-thumb {
        background: #4a4b4f;
        border-radius: 6px;
        border: 2px solid #2d2e32;
    }

    ::-webkit-scrollbar-thumb:hover {
        background: #667eea;
    }

    /* ============================================ */
    /* Markdown 스타일링 */
    /* ============================================ */

    .markdown-text h1,
    .markdown-text h2,
    .markdown-text h3 {
        color: #e5e7eb !important;
        font-weight: 700 !important;
        margin-top: 24px !important;
        margin-bottom: 16px !important;
    }

    .markdown-text h1 {
        font-size: 2em !important;
        border-bottom: 2px solid #4a4b4f !important;
        padding-bottom: 8px !important;
    }

    .markdown-text h2 {
        font-size: 1.5em !important;
    }

    .markdown-text h3 {
        font-size: 1.25em !important;
    }

    .markdown-text p {
        color: #e5e7eb !important;
        line-height: 1.7 !important;
        margin-bottom: 12px !important;
    }

    .markdown-text code {
        background: #3a3b3f !important;
        color: #667eea !important;
        padding: 2px 6px !important;
        border-radius: 4px !important;
        font-family: 'JetBrains Mono', monospace !important;
    }

    .markdown-text pre {
        background: #2d2e32 !important;
        border: 1px solid #4a4b4f !important;
        border-radius: 8px !important;
        padding: 16px !important;
        overflow-x: auto !important;
    }

    .markdown-text ul,
    .markdown-text ol {
        color: #e5e7eb !important;
        padding-left: 24px !important;
    }

    .markdown-text li {
        margin-bottom: 8px !important;
    }

    .markdown-text a {
        color: #667eea !important;
        text-decoration: none !important;
        transition: color 0.3s ease !important;
    }

    .markdown-text a:hover {
        color: #5568d3 !important;
        text-decoration: underline !important;
    }

    .markdown-text hr {
        border: none !important;
        border-top: 1px solid #4a4b4f !important;
        margin: 24px 0 !important;
    }
    """
