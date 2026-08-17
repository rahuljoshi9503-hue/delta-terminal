from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
import gemini_engine

router = APIRouter(prefix="/api/ai", tags=["Gemini AI Copilot"])

class StrategyPromptRequest(BaseModel):
    user_id: Optional[int] = 1
    prompt: str
    asset: str = "BTCUSD"

@router.post("/generate-strategy")
def generate_strategy(data: StrategyPromptRequest):
    # १. Gemini कडून स्ट्रॅटेजी तयार करणे
    strategy_json = gemini_engine.generate_strategy_from_prompt(data.prompt, data.asset)

    if isinstance(strategy_json, dict) and strategy_json.get("status") == "error":
        raise HTTPException(
            status_code=500,
            detail=strategy_json.get("message", "Gemini Engine Error")
        )

    # २. बॅकटेस्ट सिम्युलेशन चालवणे
    mock_candles = [{"close": 60000 + i * 10} for i in range(50)]
    backtest_result = gemini_engine.run_simple_backtest(strategy_json, mock_candles)

    return {
        "status": "success",
        "strategy": strategy_json,
        "backtest": backtest_result
    }