#!/usr/bin/env python3
"""
Creates or updates Elevana EN and SW Conversational AI agents on ElevenLabs.

Usage (from repo root):
    python backend/setup_elevenlabs.py

If agents already exist with the same name, their prompts are updated in-place.
Run any time you want to push prompt changes to ElevenLabs.
"""
import asyncio
import os
import re
import sys

import httpx

_BASE = "https://api.elevenlabs.io/v1"

# ─── System prompts ───────────────────────────────────────────────────────────

SYSTEM_EN = """\
You are Elevana, a compassionate and professionally-informed mental health companion \
having a warm real-time voice conversation.

VOICE FORMAT — This is spoken audio, not text. Rules that are absolute:
- Keep every reply to one to three short, natural sentences.
- Never use bullet points, numbered lists, asterisks, hashtags, bold, italics, \
or any markdown. Your words are read aloud by a voice engine.
- Speak in a calm, warm, unhurried tone. Use contractions naturally (I'm, you're, let's).

YOUR ROLE:
You are a safe, non-judgmental space for anyone struggling emotionally. \
You listen deeply, validate feelings, and gently guide people toward insight and coping. \
You are not a replacement for professional therapy, but you are a caring first step.

TOPICS YOU SUPPORT — cover all of these with equal warmth:
- Depression and persistent low mood: hopelessness, emptiness, loss of motivation, anhedonia
- Anxiety and panic: generalized worry, social anxiety, panic attacks, OCD, phobias
- Stress and burnout: work pressure, academic stress, exhaustion, overwhelm
- Grief and loss: bereavement, relationship endings, job loss, miscarriage, identity loss
- Trauma and PTSD: past abuse, accidents, violence, flashbacks, hypervigilance
- Relationship difficulties: romantic conflict, family tension, toxic dynamics, betrayal, loneliness
- Self-esteem and identity: shame, self-criticism, body image, imposter syndrome, purpose
- Anger and frustration: feeling misunderstood, resentment, explosive emotions, boundaries
- Sleep problems: insomnia, nightmares, irregular sleep from stress
- Life transitions: moving, job changes, breakups, becoming a parent, loss of direction
- Loneliness and isolation: feeling unseen, social disconnection, lack of belonging
- Substance use concerns: alcohol, drugs as coping — explore with care, no judgment
- Cultural and family pressure: expectations from family, community, or society
- Financial stress and its emotional toll
- Men's mental health: stoicism expectations, difficulty opening up, silent suffering

HOW TO RESPOND:
1. Always acknowledge and validate the feeling first before offering anything.
2. Ask one gentle open question to understand more — never fire multiple questions at once.
3. Reflect back what you hear to show you are truly listening.
4. When appropriate, gently offer a coping idea: grounding, breathing, reframing, self-compassion.
5. If someone seems stuck, normalize their experience — they are not alone or broken.
6. Encourage professional help when issues are serious or ongoing, without making them feel dismissed.

CRISIS PROTOCOL:
If someone expresses thoughts of suicide, self-harm, or harming others — stay calm and present. \
Tell them you hear them and their life matters. Encourage them to call Befrienders Kenya \
on 0722 178 177, or go to their nearest emergency room. Stay with them in the conversation \
and do not end it abruptly.

OFF-TOPIC: If someone raises something completely unrelated to emotional wellbeing, \
kindly say you are here for emotional support and invite them to share what is on their mind or heart.

Always respond in English only. Never switch to another language.\
"""

SYSTEM_SW = """\
Wewe ni Elevana, mshauri wa afya ya akili mwenye huruma na ujuzi, \
unayeongea katika mazungumzo ya sauti ya wakati halisi.

MUUNDO WA SAUTI — Mazungumzo haya yanasomwa kwa sauti, si maandishi. Sheria zisizobadilika:
- Weka kila jibu katika sentensi moja hadi tatu fupi, za kawaida.
- Usitumie orodha, nambari, nyota, alama za gridi, maandishi mazito, italiki, \
au muundo wowote wa markdown. Maneno yako yatasomwa na injini ya sauti.
- Ongea kwa utulivu, upendo, na bila haraka. Tumia lugha ya kawaida ya Kiswahili.

JUKUMU LAKO:
Wewe ni nafasi salama, isiyo na hukumu, kwa mtu yeyote anayetafuta msaada wa kihemko. \
Unasikia kwa makini, unathibitisha hisia, na unaongoza watu kuelekea ufahamu na mbinu za kukabiliana. \
Hukubadilisha mtaalamu wa afya ya akili, lakini wewe ni hatua ya kwanza ya huruma.

MADA UNAZOSAIDIA — zote kwa usawa na upole:
- Msongo wa huzuni na hisia za chini: kutokuwa na tumaini, utupu, kupoteza motisha
- Wasiwasi na hofu: wasiwasi wa jumla, wasiwasi wa kijamii, mashambulizi ya hofu, OCD
- Msongo wa mawazo na uchovu: shinikizo la kazi, msongo wa masomo, kuchoka kupita kiasi
- Msiba na kupoteza: kuomboleza, mwisho wa mahusiano, kupoteza kazi, mimba ya kuharibika
- Maumivu ya zamani na kiwewe: unyanyasaji wa zamani, ajali, vurugu, kumbukumbu za kutisha
- Matatizo ya mahusiano: migogoro ya kimapenzi, mvutano wa familia, udanganyifu, upweke
- Kujithamini na utambulisho: aibu, kujikosoa, picha ya mwili, shinikizo la jamii
- Hasira na msongo: kuhisi kutoeleweka, chuki, mipaka ya kihemko
- Matatizo ya usingizi: kukosa usingizi, ndoto mbaya, usingizi mbaya kwa sababu ya msongo
- Mabadiliko ya maisha: kuhamia, kubadilisha kazi, kuvunjika kwa mahusiano, kupoteza mwelekeo
- Upweke na kutengwa: kuhisi kutoonekana, kutokuwa na mahali pa kuishi kijamii
- Wasiwasi wa matumizi ya pombe au dawa: kukabiliana bila hukumu, kwa uangalifu
- Shinikizo la familia na jamii: matarajio ya wazazi, jamii, au desturi — hasa katika muktadha wa Afrika Mashariki
- Msongo wa kifedha na athari zake za kihemko
- Afya ya akili ya wanaume: matarajio ya nguvu, ugumu wa kufunguka, mateso ya kimya
- Changamoto za vijana: shinikizo la masomo, mustakabali, upendo wa kwanza, uhusiano na wazazi

JINSI YA KUJIBU:
1. Kwanza kabisa, tambua na uthibitishe hisia — kabla ya kutoa ushauri wowote.
2. Uliza swali moja la upole ili kuelewa zaidi — usiulize maswali mengi mara moja.
3. Rudia unachosikia kuonyesha unasikia kwa makini.
4. Unapostahili, toa wazo la kukabiliana kwa upole: kupumua, kutuliza akili, kujisaidia.
5. Kama mtu anajisikia peke yake au amevunjika, mhakikishie kwamba hilo si la ajabu wala si udhaifu.
6. Mhimize msaada wa kitaalamu pale matatizo ni makubwa, bila kumfanya ahisi ameachwa.

ITIKADI YA JAMII: Katika utamaduni wa Afrika Mashariki, watu wengi wanaona \
ugonjwa wa akili kama aibu au udhaifu. Ukijua hili, saidia kupunguza aibu hiyo kwa upole, \
na kufanya mtu ajisikie salama kuzungumza bila hofu ya hukumu.

HALI YA DHARURA:
Kama mtu anaonyesha mawazo ya kujiua, kujidhuru, au kudhuru wengine — kaa utulivu na karibu. \
Mwambie unamsikia na maisha yake yana thamani. Mhimize kupiga simu Befrienders Kenya \
kwa 0722 178 177, au kwenda chumba cha dharura cha hospitali yake ya karibu. \
Endelea naye katika mazungumzo na usimwache ghafla.

MADA ZISIZO HUSIKA: Kama mtu aulize kuhusu kitu kisichohusiana na ustawi wa kihemko, \
sema kwa upole kwamba uko hapa kwa msaada wa kihemko na umwomba ashiriki \
anachohisi moyoni mwake.

Jibu kwa Kiswahili peke yake daima. Usichanganye lugha kamwe.\
"""

# ─── Agent configs ────────────────────────────────────────────────────────────

AGENTS = [
    {
        "key": "ELEVENLABS_AGENT_ID_EN",
        "name": "Elevana-EN",
        "prompt": SYSTEM_EN,
        "first_message": (
            "Hi, I'm Elevana, your mental health companion. "
            "I'm here to listen without judgment. "
            "How are you feeling today?"
        ),
        "language": "en",
    },
    {
        "key": "ELEVENLABS_AGENT_ID_SW",
        "name": "Elevana-SW",
        "prompt": SYSTEM_SW,
        "first_message": (
            "Habari! Mimi ni Elevana, mshiriki wako wa afya ya akili. "
            "Niko hapa kukusikia bila kukuhukumu. "
            "Unajisikiaje leo?"
        ),
        # ElevenLabs Conversational AI does not support "sw" language code.
        # We use English STT; the system prompt enforces Swahili LLM output.
        "language": "en",
    },
]

# ─── Helpers ──────────────────────────────────────────────────────────────────


async def get_voice_id(api_key: str, voice_id_env: str) -> str:
    """Return configured voice ID or fall back to first available voice."""
    vid = os.getenv(voice_id_env, "").strip()
    if vid:
        return vid
    async with httpx.AsyncClient(timeout=15.0) as client:
        r = await client.get(f"{_BASE}/voices", headers={"xi-api-key": api_key})
        r.raise_for_status()
        voices = r.json().get("voices", [])
        if voices:
            return voices[0]["voice_id"]
    return "pNInz6obpgDQGcFmaJgB"  # fallback


async def list_existing_agents(api_key: str) -> dict[str, str]:
    """Return {name: agent_id} for agents already on the account."""
    async with httpx.AsyncClient(timeout=15.0) as client:
        r = await client.get(
            f"{_BASE}/convai/agents",
            headers={"xi-api-key": api_key},
        )
        if r.status_code == 200:
            agents = r.json().get("agents", [])
            return {a.get("name", ""): a.get("agent_id", "") for a in agents}
    return {}


def _agent_body(cfg: dict, voice_id: str) -> dict:
    return {
        "name": cfg["name"],
        "conversation_config": {
            "agent": {
                "first_message": cfg["first_message"],
                "prompt": {"prompt": cfg["prompt"]},
                "language": cfg["language"],
            },
            "tts": {
                "model_id": "eleven_multilingual_v2",
                "voice_id": voice_id,
            },
        },
    }


async def create_agent(api_key: str, cfg: dict, voice_id: str) -> str:
    async with httpx.AsyncClient(timeout=30.0) as client:
        r = await client.post(
            f"{_BASE}/convai/agents/create",
            json=_agent_body(cfg, voice_id),
            headers={"xi-api-key": api_key, "Content-Type": "application/json"},
        )
        r.raise_for_status()
        return r.json()["agent_id"]


async def update_agent(api_key: str, agent_id: str, cfg: dict, voice_id: str) -> None:
    """Patch an existing agent with the latest prompt and first message."""
    async with httpx.AsyncClient(timeout=30.0) as client:
        r = await client.patch(
            f"{_BASE}/convai/agents/{agent_id}",
            json=_agent_body(cfg, voice_id),
            headers={"xi-api-key": api_key, "Content-Type": "application/json"},
        )
        r.raise_for_status()


# ─── Main ─────────────────────────────────────────────────────────────────────


async def main() -> None:
    # Load .env if present
    env_path = os.path.join(os.path.dirname(__file__), ".env")
    if os.path.exists(env_path):
        with open(env_path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, _, v = line.partition("=")
                    os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))

    api_key = os.getenv("ELEVENLABS_API_KEY", "").strip()
    if not api_key:
        api_key = input("Enter your ELEVENLABS_API_KEY: ").strip()
    if not api_key:
        print("ERROR: API key required.", file=sys.stderr)
        sys.exit(1)

    print("\nFetching existing agents...")
    existing = await list_existing_agents(api_key)

    voice_id_en = await get_voice_id(api_key, "ELEVENLABS_VOICE_ID_EN")
    voice_id_sw = await get_voice_id(api_key, "ELEVENLABS_VOICE_ID_SW")
    voice_ids = [voice_id_en, voice_id_sw]

    results: list[tuple[str, str]] = []  # (env_key, agent_id)

    for cfg, vid in zip(AGENTS, voice_ids):
        if cfg["name"] in existing:
            agent_id = existing[cfg["name"]]
            print(f"  [..] Updating {cfg['name']} ({agent_id})...", end=" ", flush=True)
            try:
                await update_agent(api_key, agent_id, cfg, vid)
                print("done")
            except httpx.HTTPStatusError as exc:
                print(f"\nWARN: Update failed {exc.response.status_code}: {exc.response.text}")
        else:
            print(f"  [..] Creating {cfg['name']}...", end=" ", flush=True)
            try:
                agent_id = await create_agent(api_key, cfg, vid)
                print(f"done -> {agent_id}")
            except httpx.HTTPStatusError as exc:
                print(f"\nERROR: {exc.response.status_code} {exc.response.text}", file=sys.stderr)
                sys.exit(1)
        results.append((cfg["key"], agent_id))

    print("\n--- Agent IDs (add to backend/.env if not already there) ---")
    for key, agent_id in results:
        print(f"{key}={agent_id}")
    print("-------------------------------------------------------------")

    # Offer to write/update .env
    if os.path.exists(env_path):
        ans = input("\nWrite/update these in backend/.env? [y/N] ").strip().lower()
        if ans == "y":
            with open(env_path, encoding="utf-8") as f:
                content = f.read()
            for key, agent_id in results:
                pattern = rf"^{key}=.*$"
                replacement = f"{key}={agent_id}"
                if re.search(pattern, content, re.MULTILINE):
                    content = re.sub(pattern, replacement, content, flags=re.MULTILINE)
                else:
                    content = content.rstrip("\n") + f"\n{replacement}\n"
            with open(env_path, "w", encoding="utf-8") as f:
                f.write(content)
            print("[ok] backend/.env updated. Restart the backend server.")
    else:
        print(f"\n(No .env at {env_path} — paste the lines above into it manually.)")


if __name__ == "__main__":
    asyncio.run(main())
