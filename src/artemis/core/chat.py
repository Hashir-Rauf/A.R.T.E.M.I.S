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
Talk naturally. Keep answers short: a few sentences unless the user asks for detail.
Use plain sentences, not headings or tables. You can discuss anything.

Be honest about what you can do. From this chat the user can ask you to:
tidy a folder, answer questions about the files in the chosen folder (with the
file each point came from), suggest a fix to a code file as a diff, draft a
document, search the web, or write an email. Anything that changes a file,
searches the web or sends an email waits for the user's approval first.
You cannot delete files, and you never see files outside the folders the user
has added. You have not looked at any file in this reply.
Never claim to have done something you have not done. You cannot send or draft an email from this
chat reply, so never say you drafted or sent one: if the user wants an email, ask who it goes to
and what it should say, and the app will prepare it for approval.
"""


#: Added when the person is talking rather than typing, so the reply sounds like a
#: person on a call and not a written answer read out.
VOICE_STYLE = """
This is a spoken conversation, so talk like a friendly person on a phone call:
one to three short sentences, everyday words and contractions, no lists, no
markdown, no emoji. React to what they just said before anything else. When it
fits, end with a short question or an offer, the way people keep a chat going.
Speak clearly and warmly in normal, correctly spelled English: do not imitate
an accent or drop letters. Never say which model or software you are; you are just ARTEMIS.
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
        #: True while the person is talking, which changes how the reply is worded.
        self.spoken = False

    def reply(
        self,
        workspace_id: int | None,
        message: str,
        history: list[tuple[str, str]] | None = None,
    ) -> ChatReply:
        """Answer one message. `history` is (what the user said, what ARTEMIS said)."""
        prompt = self._prompt(message, history or [], self.spoken)
        decision = self._router.complete(
            workspace_id, prompt, max_tokens=250 if self.spoken else 700, think=False
        )
        provider = next(
            (p for p in self._router.providers if p.name == decision.completion.provider),
            None,
        )
        model = getattr(provider, "model", decision.completion.provider)
        local = decision.completion.tier == ModelTier.LOCAL
        where = "on this computer" if local else f"via {decision.completion.provider}"
        return ChatReply(decision.completion.text.strip(), model, where)

    def stream_reply(
        self,
        workspace_id: int | None,
        message: str,
        history: list[tuple[str, str]] | None = None,
    ):
        """Yield (text so far, label). The label is empty until the reply is complete."""
        prompt = self._prompt(message, history or [], self.spoken)
        text = ""
        limit = 250 if self.spoken else 700
        for piece in self._router.stream(workspace_id, prompt, max_tokens=limit, think=False):
            text += piece
            yield text, ""
        provider = self._router.last_streamed
        model = getattr(provider, "model", "")
        local = getattr(provider, "tier", None) == ModelTier.LOCAL
        where = "on this computer" if local else f"via {getattr(provider, 'name', 'cloud')}"
        yield text.strip(), f"{model} \u00b7 {where}"

    @staticmethod
    def _prompt(message: str, history: list[tuple[str, str]], spoken: bool = False) -> str:
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
            f"{SYSTEM}{VOICE_STYLE if spoken else ''}\n"
            + (f"Conversation so far:\n{earlier}\n" if earlier else "")
            + f"User: {message}\nARTEMIS:"
        )
