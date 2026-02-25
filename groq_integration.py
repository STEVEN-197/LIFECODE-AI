"""
Groq AI Integration - Llama-3.3-70b-versatile
Health analysis with streaming enabled
"""

import os
from groq import Groq
from typing import Dict, Optional


class GroqHealthAnalyzer:

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv('GROQ_API_KEY', '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')
        self.client  = Groq(api_key=self.api_key) if self.api_key else None
        self.model   = 'llama-3.3-70b-versatile'

    def analyze_health_profile(self, predictions: Dict,
                                lifestyle: Dict,
                                medical: Optional[Dict] = None) -> Dict:
        if not self.client:
            return {'success': False, 'analysis': self._fallback(predictions)}
        try:
            prompt   = self._build_prompt(predictions, lifestyle, medical)
            response = self._call_api(prompt)
            return {'success': True, 'analysis': response}
        except Exception as e:
            return {'success': False, 'analysis': self._fallback(predictions)}

    def _build_prompt(self, predictions, lifestyle, medical):
        sensor_mode = medical.get('sensor_mode', 'Virtual') if medical else 'Virtual'
        return f"""You are a health advisor analyzing biosensor data.

## ML Predictions
- Stress Index:     {predictions['stress_index']:.1f}/100
- Metabolic Score:  {predictions['metabolic_score']:.1f}/100
- Lifestyle Risk:   {predictions['lifestyle_risk']:.1f}/100

## Lifestyle
- Sleep: {lifestyle.get('sleep')} hrs/night
- Diet:  {lifestyle.get('food_habit')}
- Activity: {lifestyle.get('activity')} hrs/week
- Stress: {lifestyle.get('stress')}/10

## Biosensor Data ({sensor_mode})
- Heart Rate:   {medical.get('heart_rate') if medical else 'N/A'} BPM
- GSR:          {medical.get('gsr') if medical else 'N/A'} uS
- Temperature:  {medical.get('temperature') if medical else 'N/A'} C
- Glucose:      {medical.get('glucose') if medical else 'N/A'} mg/dL
- Cholesterol:  {medical.get('cholesterol') if medical else 'N/A'} mg/dL

Provide:
1. Overall Health Summary (2-3 sentences)
2. Key Risks (3 bullet points)
3. Actionable Recommendations (5 specific steps)
4. Positive Strengths (2 things they are doing well)

Use clear markdown. Be empathetic and evidence-based.
Always remind: consult a healthcare professional for medical decisions."""

    def _call_api(self, prompt: str) -> str:
        completion = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system",
                 "content": "You are a knowledgeable, empathetic health advisor. Always recommend consulting healthcare professionals."},
                {"role": "user", "content": prompt}
            ],
            temperature=1,
            max_completion_tokens=2048,
            top_p=1,
            stream=True,
            stop=None
        )
        result = ''
        for chunk in completion:
            result += chunk.choices[0].delta.content or ''
        return result

    def _fallback(self, predictions: Dict) -> str:
        s   = float(predictions['stress_index'])
        r   = float(predictions['lifestyle_risk'])
        m   = float(predictions['metabolic_score'])
        out = '## Health Analysis\n\n'
        out += f'- **Stress Index:** {s:.1f}/100 - {"High" if s > 70 else "Manageable"}\n'
        out += f'- **Metabolic Score:** {m:.1f}/100 - {"Good" if m > 60 else "Needs improvement"}\n'
        out += f'- **Lifestyle Risk:** {r:.1f}/100 - {"High" if r > 70 else "Low"}\n\n'
        out += '*AI analysis unavailable - showing basic summary.*'
        return out
