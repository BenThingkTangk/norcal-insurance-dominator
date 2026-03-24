#!/usr/bin/env python3
"""NorCal Insurance Dominator — AI Backend Server
Endpoints for the AI Recruiting Agent, Objection Handler, and Pitch Generator."""

import json, os, re
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from anthropic import Anthropic
from pydantic import BaseModel
from typing import Optional

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
client = Anthropic()

# ═══════ REAL DATA: NorCal County FAIR Plan Data (from cfpnet.com FY2025) ═══════
NORCAL_COUNTIES = {
    "Alameda": {"fair_plan_policies": 11694, "yoy_growth": "73%", "pop": 1682353, "risk": "Moderate", "top_carriers_exited": ["State Farm", "Allstate"], "fire_hazard": "High in hills"},
    "Alpine": {"fair_plan_policies": 392, "yoy_growth": "13%", "pop": 1204, "risk": "Very High", "top_carriers_exited": ["Most carriers"], "fire_hazard": "Very High"},
    "Amador": {"fair_plan_policies": 6186, "yoy_growth": "13%", "pop": 41259, "risk": "Very High", "top_carriers_exited": ["State Farm", "Nationwide"], "fire_hazard": "Very High"},
    "Butte": {"fair_plan_policies": 9392, "yoy_growth": "15%", "pop": 211632, "risk": "Very High", "top_carriers_exited": ["State Farm", "Allstate", "Nationwide"], "fire_hazard": "Very High — Camp Fire history"},
    "Calaveras": {"fair_plan_policies": 10572, "yoy_growth": "11%", "pop": 46221, "risk": "Very High", "top_carriers_exited": ["State Farm", "Farmers"], "fire_hazard": "Very High"},
    "Colusa": {"fair_plan_policies": 68, "yoy_growth": "42%", "pop": 22401, "risk": "Low", "top_carriers_exited": [], "fire_hazard": "Moderate"},
    "Contra Costa": {"fair_plan_policies": 12837, "yoy_growth": "96%", "pop": 1165927, "risk": "High", "top_carriers_exited": ["State Farm", "Allstate"], "fire_hazard": "High in east hills"},
    "Del Norte": {"fair_plan_policies": 572, "yoy_growth": "62%", "pop": 27743, "risk": "Moderate", "top_carriers_exited": ["Nationwide"], "fire_hazard": "Moderate"},
    "El Dorado": {"fair_plan_policies": 28167, "yoy_growth": "18%", "pop": 193221, "risk": "Extreme", "top_carriers_exited": ["State Farm", "Allstate", "Nationwide", "Farmers"], "fire_hazard": "Very High — Caldor Fire history"},
    "Fresno": {"fair_plan_policies": 5821, "yoy_growth": "25%", "pop": 1013581, "risk": "Moderate", "top_carriers_exited": ["State Farm"], "fire_hazard": "Moderate-High in foothills"},
    "Glenn": {"fair_plan_policies": 58, "yoy_growth": "18%", "pop": 29316, "risk": "Low", "top_carriers_exited": [], "fire_hazard": "Low-Moderate"},
    "Humboldt": {"fair_plan_policies": 2844, "yoy_growth": "38%", "pop": 135558, "risk": "High", "top_carriers_exited": ["Nationwide"], "fire_hazard": "High"},
    "Lake": {"fair_plan_policies": 5739, "yoy_growth": "19%", "pop": 67750, "risk": "Extreme", "top_carriers_exited": ["State Farm", "Allstate", "Farmers"], "fire_hazard": "Very High — Valley Fire history"},
    "Lassen": {"fair_plan_policies": 1064, "yoy_growth": "32%", "pop": 31345, "risk": "Very High", "top_carriers_exited": ["State Farm", "Nationwide"], "fire_hazard": "Very High — Dixie Fire history"},
    "Madera": {"fair_plan_policies": 5650, "yoy_growth": "19%", "pop": 159410, "risk": "High", "top_carriers_exited": ["State Farm"], "fire_hazard": "High in foothills"},
    "Marin": {"fair_plan_policies": 4361, "yoy_growth": "51%", "pop": 262321, "risk": "High", "top_carriers_exited": ["State Farm", "Allstate"], "fire_hazard": "High — WUI zones"},
    "Mariposa": {"fair_plan_policies": 3404, "yoy_growth": "11%", "pop": 17540, "risk": "Extreme", "top_carriers_exited": ["Most carriers"], "fire_hazard": "Very High"},
    "Mendocino": {"fair_plan_policies": 4707, "yoy_growth": "22%", "pop": 91601, "risk": "Very High", "top_carriers_exited": ["State Farm", "Farmers"], "fire_hazard": "Very High"},
    "Merced": {"fair_plan_policies": 336, "yoy_growth": "68%", "pop": 286461, "risk": "Low", "top_carriers_exited": [], "fire_hazard": "Low"},
    "Modoc": {"fair_plan_policies": 290, "yoy_growth": "49%", "pop": 8661, "risk": "Very High", "top_carriers_exited": ["Most carriers"], "fire_hazard": "Very High"},
    "Mono": {"fair_plan_policies": 1982, "yoy_growth": "45%", "pop": 13247, "risk": "Very High", "top_carriers_exited": ["Most carriers"], "fire_hazard": "Very High"},
    "Monterey": {"fair_plan_policies": 5402, "yoy_growth": "28%", "pop": 439035, "risk": "High", "top_carriers_exited": ["State Farm"], "fire_hazard": "High in Big Sur / Carmel Valley"},
    "Napa": {"fair_plan_policies": 3042, "yoy_growth": "25%", "pop": 138019, "risk": "Very High", "top_carriers_exited": ["State Farm", "Allstate"], "fire_hazard": "Very High — Glass Fire history"},
    "Nevada": {"fair_plan_policies": 23438, "yoy_growth": "18%", "pop": 103487, "risk": "Extreme", "top_carriers_exited": ["State Farm", "Allstate", "Nationwide", "Farmers"], "fire_hazard": "Very High"},
    "Placer": {"fair_plan_policies": 18996, "yoy_growth": "21%", "pop": 412300, "risk": "Very High", "top_carriers_exited": ["State Farm", "Allstate", "Nationwide"], "fire_hazard": "Very High in east county"},
    "Plumas": {"fair_plan_policies": 3941, "yoy_growth": "13%", "pop": 19790, "risk": "Extreme", "top_carriers_exited": ["Most carriers"], "fire_hazard": "Very High — Dixie Fire history"},
    "Sacramento": {"fair_plan_policies": 2001, "yoy_growth": "78%", "pop": 1585055, "risk": "Low", "top_carriers_exited": [], "fire_hazard": "Low-Moderate"},
    "San Benito": {"fair_plan_policies": 388, "yoy_growth": "73%", "pop": 66677, "risk": "Moderate", "top_carriers_exited": [], "fire_hazard": "Moderate"},
    "San Francisco": {"fair_plan_policies": 2382, "yoy_growth": "76%", "pop": 873965, "risk": "Low", "top_carriers_exited": [], "fire_hazard": "Low"},
    "San Joaquin": {"fair_plan_policies": 1319, "yoy_growth": "57%", "pop": 789410, "risk": "Low", "top_carriers_exited": [], "fire_hazard": "Low"},
    "San Mateo": {"fair_plan_policies": 3759, "yoy_growth": "66%", "pop": 764442, "risk": "Moderate", "top_carriers_exited": ["State Farm"], "fire_hazard": "Moderate-High in hills"},
    "Santa Clara": {"fair_plan_policies": 6200, "yoy_growth": "69%", "pop": 1936259, "risk": "Moderate", "top_carriers_exited": ["State Farm"], "fire_hazard": "High in south county hills"},
    "Santa Cruz": {"fair_plan_policies": 12796, "yoy_growth": "60%", "pop": 270861, "risk": "Very High", "top_carriers_exited": ["State Farm", "Allstate"], "fire_hazard": "Very High — CZU Fire history"},
    "Shasta": {"fair_plan_policies": 6505, "yoy_growth": "25%", "pop": 182155, "risk": "Very High", "top_carriers_exited": ["State Farm", "Farmers"], "fire_hazard": "Very High — Carr Fire history"},
    "Sierra": {"fair_plan_policies": 541, "yoy_growth": "13%", "pop": 3236, "risk": "Extreme", "top_carriers_exited": ["Most carriers"], "fire_hazard": "Very High"},
    "Siskiyou": {"fair_plan_policies": 3269, "yoy_growth": "31%", "pop": 44076, "risk": "Very High", "top_carriers_exited": ["State Farm", "Nationwide"], "fire_hazard": "Very High"},
    "Solano": {"fair_plan_policies": 1312, "yoy_growth": "83%", "pop": 453491, "risk": "Low", "top_carriers_exited": [], "fire_hazard": "Low-Moderate"},
    "Sonoma": {"fair_plan_policies": 8748, "yoy_growth": "39%", "pop": 488863, "risk": "Very High", "top_carriers_exited": ["State Farm", "Allstate", "Farmers"], "fire_hazard": "Very High — Tubbs/Kincade history"},
    "Stanislaus": {"fair_plan_policies": 743, "yoy_growth": "78%", "pop": 552878, "risk": "Low", "top_carriers_exited": [], "fire_hazard": "Low"},
    "Sutter": {"fair_plan_policies": 118, "yoy_growth": "131%", "pop": 99063, "risk": "Low", "top_carriers_exited": [], "fire_hazard": "Low"},
    "Tehama": {"fair_plan_policies": 1783, "yoy_growth": "19%", "pop": 65498, "risk": "Very High", "top_carriers_exited": ["State Farm"], "fire_hazard": "Very High"},
    "Trinity": {"fair_plan_policies": 1440, "yoy_growth": "11%", "pop": 16060, "risk": "Extreme", "top_carriers_exited": ["Most carriers"], "fire_hazard": "Very High"},
    "Tulare": {"fair_plan_policies": 2966, "yoy_growth": "27%", "pop": 477054, "risk": "Moderate", "top_carriers_exited": ["State Farm"], "fire_hazard": "High in foothills"},
    "Tuolumne": {"fair_plan_policies": 14071, "yoy_growth": "9%", "pop": 55810, "risk": "Extreme", "top_carriers_exited": ["Most carriers"], "fire_hazard": "Very High"},
    "Yolo": {"fair_plan_policies": 251, "yoy_growth": "29%", "pop": 216403, "risk": "Low", "top_carriers_exited": [], "fire_hazard": "Low-Moderate"},
    "Yuba": {"fair_plan_policies": 1569, "yoy_growth": "11%", "pop": 82275, "risk": "Moderate", "top_carriers_exited": ["State Farm"], "fire_hazard": "High"},
}

# ═══════ CARRIER EXIT INTELLIGENCE (real data through March 2026) ═══════
CARRIER_INTEL = {
    "State Farm": {"status": "Halted ALL new homeowners in CA since May 2023", "impact": "Largest P&C insurer in CA — agents cannot write new HO business", "opportunity": "Agents are trapped — can't grow, losing clients to non-renewals. Biggest recruiting pool in NorCal.", "talking_point": "Your book is a melting ice cube. Every non-renewal is a client lost forever unless you move now."},
    "Allstate": {"status": "Stopped new homeowners and condo policies in CA since Nov 2022", "impact": "Complete exit from new personal lines", "opportunity": "Allstate agents have zero growth path in CA homeowners. They're watching their book shrink.", "talking_point": "Allstate has abandoned California homeowners. Your clients are getting non-renewal letters. I have carriers actively writing."},
    "Farmers": {"status": "Reduced new auto policies by ~25%, capped homeowners in fire zones since July 2023", "impact": "Severe growth limitations in NorCal fire risk counties", "opportunity": "Farmers agents in foothill/mountain counties are effectively frozen — can't write new business.", "talking_point": "Farmers has capped your growth. You can't write new homeowners in your own territory. That's not a career — that's a waiting room."},
    "Nationwide/Crestbrook": {"status": "Completely exited California personal lines — non-renewed ALL policies", "impact": "Total exit — every policyholder displaced", "opportunity": "Former Nationwide agents need a new home immediately.", "talking_point": "Nationwide didn't just stop writing — they LEFT. Every client you had is now someone else's client unless you act."},
    "AIG (Lexington)": {"status": "Reduced high-value home exposure in CA wildfire zones", "impact": "High-net-worth clients losing E&S options", "opportunity": "Agents serving HNW clients need alternative E&S markets.", "talking_point": "Your high-net-worth clients are losing Lexington coverage. I can connect you with Burns & Wilcox, Scottsdale, and other E&S markets."},
    "Hartford": {"status": "Still writing but restricting new business in high-risk zones", "impact": "Selective underwriting — turning down many apps", "opportunity": "Hartford agents dealing with increased declines.", "talking_point": "Hartford is cherry-picking which risks they'll write. If you're tired of submitting apps that get declined, let's talk about platforms with broader appetites."},
    "CSAA/AAA": {"status": "Tightening underwriting in WUI zones since 2024", "impact": "Increasing non-renewals and restrictions", "opportunity": "AAA agents losing renewals in foothill communities.", "talking_point": "CSAA is quietly non-renewing in wildfire zones. Your AAA members are losing coverage. I have solutions."},
    "Mercury": {"status": "Pulled back from high-wildfire-risk areas", "impact": "Declining new apps in mountain/foothill areas", "opportunity": "Mercury agents losing access to their own territory.", "talking_point": "Mercury won't write where you live and work. Why stay with a carrier that's retreating from your own neighborhood?"},
}

SYSTEM_PROMPT_BASE = """You are the NorCal Insurance Dominator AI — an elite insurance recruiting intelligence system built for a recruiter who recruits insurance agents and agencies in Northern California.

You have deep expertise in:
- California insurance market crisis (carrier exits, FAIR Plan explosion, wildfire risk)
- Insurance recruiting tactics and psychology
- NorCal county-by-county market intelligence
- Objection handling for insurance agent recruiting
- Emotional intelligence and persuasion techniques

REAL DATA YOU KNOW (California FAIR Plan FY2025, as of 9/30/2025):
- Total FAIR Plan policies in force: 642,010 (39% YoY growth)
- Total FAIR Plan exposure: $724 BILLION
- Total written premium: $1.98 BILLION
- NorCal counties with highest FAIR Plan concentration:
  * El Dorado: 28,167 policies (18% growth)
  * Nevada County: 23,438 policies (18% growth)
  * Placer: 18,996 policies (21% growth)
  * Tuolumne: 14,071 policies (9% growth)
  * Contra Costa: 12,837 policies (96% growth — exploding)
  * Santa Cruz: 12,796 policies (60% growth)
  * Calaveras: 10,572 policies (11% growth)
  * Alameda: 11,694 policies (73% growth)
  * Butte: 9,392 policies (15% growth)
  * Sonoma: 8,748 policies (39% growth)

CARRIER EXIT INTELLIGENCE:
""" + json.dumps(CARRIER_INTEL, indent=2) + """

COUNTY DATA:
""" + json.dumps({k: v for k, v in NORCAL_COUNTIES.items()}, indent=2) + """

RULES:
- Be direct, confident, and action-oriented. You are a recruiting weapon, not a generic chatbot.
- Use specific numbers, county data, and carrier intelligence in every response.
- Speak like a top-performing recruiter — assertive but not aggressive.
- Reference real data points to build credibility.
- When generating pitches, tailor them to the specific prospect's carrier, county, and lines of business.
- For objections, provide word-for-word rebuttals with data backing.
"""

# ═══════ REQUEST MODELS ═══════
class ChatRequest(BaseModel):
    messages: list
    system_context: Optional[str] = None

class PitchRequest(BaseModel):
    prospect_name: str
    carrier: Optional[str] = None
    county: Optional[str] = None
    lines: Optional[str] = None
    experience_years: Optional[int] = None
    book_size: Optional[int] = None
    pain_points: Optional[str] = None
    stage: Optional[str] = None

class ObjectionRequest(BaseModel):
    objection: str
    prospect_context: Optional[str] = None

class IntelRequest(BaseModel):
    county: Optional[str] = None
    carrier: Optional[str] = None
    query: Optional[str] = None

# ═══════ STREAMING CHAT ENDPOINT ═══════
@app.post("/api/chat")
async def chat_stream(req: ChatRequest):
    system = SYSTEM_PROMPT_BASE
    if req.system_context:
        system += "\n\nADDITIONAL CONTEXT:\n" + req.system_context

    def generate():
        with client.messages.stream(
            model="claude_sonnet_4_6",
            max_tokens=2048,
            system=system,
            messages=req.messages,
        ) as stream:
            for text in stream.text_stream:
                yield f"data: {json.dumps({'text': text})}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")

# ═══════ TAILORED PITCH GENERATOR ═══════
@app.post("/api/pitch")
async def generate_pitch(req: PitchRequest):
    county_data = NORCAL_COUNTIES.get(req.county, {}) if req.county else {}
    carrier_data = None
    if req.carrier:
        for k, v in CARRIER_INTEL.items():
            if k.lower() in req.carrier.lower() or req.carrier.lower() in k.lower():
                carrier_data = v
                break

    pitch_prompt = f"""Generate a tailored, high-impact recruiting pitch for this specific prospect. Make it personal, data-driven, and emotionally compelling.

PROSPECT PROFILE:
- Name: {req.prospect_name}
- Current Carrier/Agency: {req.carrier or 'Unknown'}
- County: {req.county or 'Unknown'}
- Lines of Business: {req.lines or 'Unknown'}
- Years of Experience: {req.experience_years or 'Unknown'}
- Book Size: {'$' + f'{req.book_size:,}' if req.book_size else 'Unknown'}
- Known Pain Points: {req.pain_points or 'None specified'}
- Pipeline Stage: {req.stage or 'Unknown'}

{"COUNTY INTEL: " + json.dumps(county_data) if county_data else ""}
{"CARRIER INTEL: " + json.dumps(carrier_data) if carrier_data else ""}

Generate a pitch with these sections:
1. **OPENING HOOK** — A bold, personalized opening line that references their specific situation (county fire risk, carrier exit, book size concern). Maximum 2 sentences.
2. **PAIN AMPLIFICATION** — 2-3 sentences that make their current pain real with specific data (FAIR Plan numbers, carrier restrictions, market trends in their county).
3. **THE BRIDGE** — What you offer that solves their specific problem. Reference E&S markets, alternative carriers, or growth opportunities relevant to their lines.
4. **SOCIAL PROOF** — A brief reference to other agents in similar situations who've made the move.
5. **CALL TO ACTION** — A specific, time-bounded next step (not generic "let's chat").
6. **EMOTIONAL INTELLIGENCE NOTES** — Brief coaching notes on tone, pacing, and what emotional triggers to watch for with this prospect type.

Be specific. Use real data. No generic fluff."""

    def generate():
        with client.messages.stream(
            model="claude_sonnet_4_6",
            max_tokens=2048,
            system=SYSTEM_PROMPT_BASE,
            messages=[{"role": "user", "content": pitch_prompt}],
        ) as stream:
            for text in stream.text_stream:
                yield f"data: {json.dumps({'text': text})}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")

# ═══════ OBJECTION HANDLER ═══════
@app.post("/api/objection")
async def handle_objection(req: ObjectionRequest):
    objection_prompt = f"""A prospect just hit me with this objection during a recruiting conversation:

OBJECTION: "{req.objection}"

{"PROSPECT CONTEXT: " + req.prospect_context if req.prospect_context else ""}

Generate a powerful response with:

1. **ACKNOWLEDGE** — Show you heard them (1 sentence, empathetic, not dismissive)
2. **REFRAME** — Flip the objection into an opportunity using specific data (2-3 sentences with real CA insurance market data)
3. **WORD-FOR-WORD REBUTTAL** — The exact words to say right now, in quotes, conversational tone, confident but not pushy
4. **FOLLOW-UP QUESTION** — A strategic question that keeps the conversation going and digs deeper into their real concern
5. **EMOTIONAL READ** — What they're really feeling underneath this objection and how to address the emotion, not just the logic
6. **IF THEY PUSH BACK AGAIN** — A second-level response if they double down on this objection

Be direct and tactical. This is a live conversation — I need something I can say RIGHT NOW."""

    def generate():
        with client.messages.stream(
            model="claude_sonnet_4_6",
            max_tokens=1500,
            system=SYSTEM_PROMPT_BASE,
            messages=[{"role": "user", "content": objection_prompt}],
        ) as stream:
            for text in stream.text_stream:
                yield f"data: {json.dumps({'text': text})}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")

# ═══════ COUNTY/CARRIER INTELLIGENCE ═══════
@app.get("/api/intel/counties")
async def get_counties():
    return NORCAL_COUNTIES

@app.get("/api/intel/carriers")
async def get_carriers():
    return CARRIER_INTEL

@app.get("/api/intel/county/{county}")
async def get_county_intel(county: str):
    data = NORCAL_COUNTIES.get(county)
    if not data:
        for k, v in NORCAL_COUNTIES.items():
            if k.lower() == county.lower():
                return {"county": k, **v}
        return {"error": "County not found"}
    return {"county": county, **data}

@app.post("/api/intel/analyze")
async def analyze_intel(req: IntelRequest):
    context_parts = []
    if req.county:
        data = NORCAL_COUNTIES.get(req.county, {})
        if data:
            context_parts.append(f"County: {req.county}\n{json.dumps(data, indent=2)}")
    if req.carrier:
        for k, v in CARRIER_INTEL.items():
            if k.lower() in req.carrier.lower() or req.carrier.lower() in k.lower():
                context_parts.append(f"Carrier: {k}\n{json.dumps(v, indent=2)}")
                break

    query = req.query or f"Give me a full intelligence briefing on {req.county or req.carrier or 'the NorCal market'}"

    def generate():
        with client.messages.stream(
            model="claude_sonnet_4_6",
            max_tokens=2048,
            system=SYSTEM_PROMPT_BASE + ("\n\nRELEVANT DATA:\n" + "\n".join(context_parts) if context_parts else ""),
            messages=[{"role": "user", "content": query}],
        ) as stream:
            for text in stream.text_stream:
                yield f"data: {json.dumps({'text': text})}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")

# ═══════ HEALTH CHECK ═══════
@app.get("/api/health")
async def health():
    return {"status": "dominating", "counties": len(NORCAL_COUNTIES), "carriers": len(CARRIER_INTEL)}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
