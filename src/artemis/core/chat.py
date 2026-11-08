"""Talking to ARTEMIS.

Until now every message was treated as a file task or a question about files, so
anything else ("hello", "explain what a hash chain is", "what did you just say?")
was forced through the file planner or the file-grounded answerer and came back
as "could not find it". There was no conversation.

This is the conversation. It is deliberately thin: the model answers, with the
last few turns for context. It reads no files and takes no actions. When a
message is about the person's files it is the answer service that replies, with
sources, and when it asks for a change it is the approval gate that handles it;
chat is only what is left over, which is most of what people say to an assistant.

It goes through the same router as everything else, so a folder that is set to
stay local keeps the conversation on this computer, and the reply says which
model answered and where it ran.
"""

from __future__ import annotations

from dataclasses import dataclass

from artemis.core.providers import ModelTier
from artemis.core.router import ModelRouter

#: How much earlier conversation is sent with a new message. A small model gets
#: slower and less accurate as its prompt grows, and an old turn rarely matters.
MAX_HISTORY_TURNS = 6
MAX_HISTORY_CHARS = 3000

SYSTEM = """You are ARTEMIS, a private assistant that runs on the user's own computer.
Talk naturally and keep answers short and useful. You can discuss anything.

Be honest about what you can do. From this chat the user can ask you to:
tidy a folder, answer questions about the files in the chosen folder (with the
file each point came from), suggest a fix to a code file as a diff, draft a
document, search the web, or write an email. Anything that changes a file,
searches the web or sends an email waits for the user's approval first.
You cannot delete files, and you never see files outside the folders the user
has added. You have not looked at any file in this reply.
Never claim to have done something you have not done.
"""


@dataclass(frozen=True)
class ChatReply:
    text: str
    #: The model that answered, for example "gemma4:e4b".
    model: str
    #: Where it ran: "on this computer" or the name of the cloud service.
    where: str

    @property
    def label(self) -> str:
        return f"{self.model} · {self.where}"


class ChatService:
    def __init__(self, router: ModelRouter) -> None:
        self._router = router

    def reply(
        self,
        workspace_id: int | None,
        message: str,
        history: list[tuple[str, str]] | None = None,
    ) -> ChatReply:
        """Answer one message. `history` is (what the user said, what ARTEMIS said)."""
        prompt = self._prompt(message, history or [])
        decision = self._router.complete(
            workspace_id, prompt, max_tokens=700, think=False
        )
        provider = next(
            (p for p in self._router.providers if p.name == decision.completion.provider),
            None,
        )
        model = getattr(provider, "model", decision.completion.provider)
        local = decision.completion.tier == ModelTier.LOCAL
        where = "on this computer" if local else f"via {decision.completion.provider}"
        return ChatReply(decision.completion.text.strip(), model, where)

    @staticmethod
    def _prompt(message: str, history: list[tuple[str, str]]) -> str:
        recent = history[-MAX_HISTORY_TURNS:]
        lines: list[str] = []
        used = 0
        for said, replied in reversed(recent):
            chunk = (f"User: {said}\n" if said else "") + f"ARTEMIS: {replied}\n"
            used += len(chunk)
            if used > MAX_HISTORY_CHARS:
                break
            lines.append(chunk)
        earlier = "".join(reversed(lines))
        return (
            f"{SYSTEM}\n"
            + (f"Conversation so far:\n{earlier}\n" if earlier else "")
            + f"User: {message}\nARTEMIS:"
        )
