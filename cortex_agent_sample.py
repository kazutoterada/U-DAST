"""
Cortex AIエージェント操作サンプル
Claude Agent SDK を使ったエージェントの基本的な操作例
"""

import anyio
from claude_agent_sdk import (
    query,
    ClaudeSDKClient,
    ClaudeAgentOptions,
    AgentDefinition,
    HookMatcher,
    ResultMessage,
    AssistantMessage,
    SystemMessage,
    TextBlock,
    CLINotFoundError,
    CLIConnectionError,
)


# ─────────────────────────────────────────────
# 1. 基本的な使い方 — query() でシンプルに実行
# ─────────────────────────────────────────────
async def basic_agent():
    """最もシンプルなエージェント実行例"""
    print("=== 1. 基本エージェント ===")

    async for message in query(
        prompt="このリポジトリに含まれるファイルの一覧と概要を教えてください。",
        options=ClaudeAgentOptions(
            cwd="/home/user/U-DAST",
            allowed_tools=["Read", "Glob", "Grep"],
            max_turns=5,
        ),
    ):
        if isinstance(message, ResultMessage):
            print(message.result)


# ─────────────────────────────────────────────
# 2. カスタムシステムプロンプト
# ─────────────────────────────────────────────
async def agent_with_system_prompt():
    """カスタムシステムプロンプトを使ったエージェント"""
    print("\n=== 2. カスタムシステムプロンプト ===")

    async for message in query(
        prompt="コードの品質を評価してください。",
        options=ClaudeAgentOptions(
            cwd="/home/user/U-DAST",
            allowed_tools=["Read", "Glob", "Grep"],
            system_prompt="""あなたはシニアソフトウェアエンジニアです。
コードレビューでは以下の観点を必ず確認してください:
1. セキュリティの脆弱性
2. パフォーマンスの問題
3. コードの可読性と保守性
具体的な行番号と改善案を提示してください。""",
            max_turns=10,
        ),
    ):
        if isinstance(message, ResultMessage):
            print(message.result)


# ─────────────────────────────────────────────
# 3. ファイル編集を許可するエージェント
# ─────────────────────────────────────────────
async def file_editing_agent():
    """ファイルの読み書きを行うエージェント (acceptEdits モード)"""
    print("\n=== 3. ファイル編集エージェント ===")

    async for message in query(
        prompt="hello.py に現在の日時を出力するコードを追記してください。",
        options=ClaudeAgentOptions(
            cwd="/home/user/U-DAST",
            allowed_tools=["Read", "Edit", "Write"],
            permission_mode="acceptEdits",  # ファイル編集を自動承認
            max_turns=5,
        ),
    ):
        if isinstance(message, ResultMessage):
            print(f"完了: {message.result}")


# ─────────────────────────────────────────────
# 4. フック — ツール実行後のログ記録
# ─────────────────────────────────────────────
async def agent_with_hooks():
    """PostToolUse フックでファイル変更を記録するエージェント"""
    print("\n=== 4. フック付きエージェント ===")

    async def log_file_change(input_data, tool_use_id, context):
        file_path = input_data.get("tool_input", {}).get("file_path", "unknown")
        print(f"  [HOOK] ファイル変更: {file_path}")
        return {}

    async for message in query(
        prompt="hello.py の内容を確認して要約してください。",
        options=ClaudeAgentOptions(
            cwd="/home/user/U-DAST",
            allowed_tools=["Read", "Glob"],
            hooks={
                "PostToolUse": [
                    HookMatcher(matcher="Read|Edit|Write", hooks=[log_file_change])
                ]
            },
            max_turns=5,
        ),
    ):
        if isinstance(message, ResultMessage):
            print(message.result)


# ─────────────────────────────────────────────
# 5. サブエージェント — 役割分担した並列処理
# ─────────────────────────────────────────────
async def agent_with_subagents():
    """専門サブエージェントを使ったオーケストレーション例"""
    print("\n=== 5. サブエージェント ===")

    async for message in query(
        prompt="code-reviewer エージェントを使ってこのリポジトリのコードをレビューしてください。",
        options=ClaudeAgentOptions(
            cwd="/home/user/U-DAST",
            allowed_tools=["Read", "Glob", "Grep", "Agent"],
            agents={
                "code-reviewer": AgentDefinition(
                    description="品質・セキュリティの観点でコードをレビューする専門エージェント。",
                    prompt="コードの品質、セキュリティ、保守性を分析し、具体的な改善提案を日本語で提供してください。",
                    tools=["Read", "Glob", "Grep"],
                )
            },
            max_turns=10,
        ),
    ):
        if isinstance(message, ResultMessage):
            print(message.result)


# ─────────────────────────────────────────────
# 6. ClaudeSDKClient — フル制御モード
# ─────────────────────────────────────────────
async def full_control_agent():
    """ClaudeSDKClient でストリーミングとライフサイクルを細かく制御する例"""
    print("\n=== 6. フル制御モード (ClaudeSDKClient) ===")

    options = ClaudeAgentOptions(
        cwd="/home/user/U-DAST",
        allowed_tools=["Read", "Glob"],
        max_turns=5,
    )

    async with ClaudeSDKClient(options=options) as client:
        await client.query("リポジトリ内の Python ファイルをすべて探して列挙してください。")

        async for message in client.receive_response():
            if isinstance(message, AssistantMessage):
                for block in message.content:
                    if isinstance(block, TextBlock):
                        # テキストをリアルタイムで出力
                        print(block.text, end="", flush=True)
        print()  # 改行


# ─────────────────────────────────────────────
# 7. セッション継続 — 前の会話を引き継ぐ
# ─────────────────────────────────────────────
async def session_resume():
    """session_id を使って前の会話コンテキストを引き継ぐ例"""
    print("\n=== 7. セッション継続 ===")

    session_id = None

    # 1回目: セッション ID を取得
    async for message in query(
        prompt="hello.py を読んで内容を把握してください。",
        options=ClaudeAgentOptions(
            cwd="/home/user/U-DAST",
            allowed_tools=["Read"],
            max_turns=3,
        ),
    ):
        if isinstance(message, SystemMessage) and message.subtype == "init":
            session_id = message.data.get("session_id")
        if isinstance(message, ResultMessage):
            print(f"1回目: {message.result[:100]}...")

    # 2回目: 同じセッションで続きの質問
    if session_id:
        async for message in query(
            prompt="さっき読んだファイルの改善点を提案してください。",
            options=ClaudeAgentOptions(resume=session_id),
        ):
            if isinstance(message, ResultMessage):
                print(f"2回目 (継続): {message.result[:200]}...")


# ─────────────────────────────────────────────
# 8. エラーハンドリング
# ─────────────────────────────────────────────
async def agent_with_error_handling():
    """エラーを適切にキャッチする例"""
    print("\n=== 8. エラーハンドリング ===")

    try:
        async for message in query(
            prompt="コードを解析してください。",
            options=ClaudeAgentOptions(
                cwd="/home/user/U-DAST",
                allowed_tools=["Read", "Glob"],
                max_turns=5,
            ),
        ):
            if isinstance(message, ResultMessage):
                print(message.result)

    except CLINotFoundError:
        print("エラー: Claude Code CLI が見つかりません。")
        print("インストール: pip install claude-agent-sdk")
    except CLIConnectionError as e:
        print(f"エラー: 接続に失敗しました — {e}")
    except Exception as e:
        print(f"予期しないエラー: {e}")


# ─────────────────────────────────────────────
# エントリーポイント
# ─────────────────────────────────────────────
async def main():
    # 実行したいサンプルをコメントアウトして切り替えてください
    await basic_agent()
    # await agent_with_system_prompt()
    # await file_editing_agent()
    # await agent_with_hooks()
    # await agent_with_subagents()
    # await full_control_agent()
    # await session_resume()
    # await agent_with_error_handling()


if __name__ == "__main__":
    anyio.run(main)
