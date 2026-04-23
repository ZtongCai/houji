import { GoogleGenAI, Type } from "@google/genai";
import { PlantStatus, PlantType } from "../types";

const ai = new GoogleGenAI({ apiKey: process.env.GEMINI_API_KEY });

export async function analyzePlantImage(base64Image: string): Promise<PlantStatus> {
  const response = await ai.models.generateContent({
    model: "gemini-3-flash-preview",
    contents: [
      {
        parts: [
          { text: "Analyze this plant photo for a smart farm dashboard. Identify the plant type (lettuce, tomato, basil, or generic), estimate its height in cm, count its visible leaves, and assess its overall health (0-100)." },
          {
            inlineData: {
              mimeType: "image/jpeg",
              data: base64Image.split(',')[1] || base64Image
            }
          }
        ]
      }
    ],
    config: {
      responseMimeType: "application/json",
      responseSchema: {
        type: Type.OBJECT,
        properties: {
          type: { type: Type.STRING, enum: ['lettuce', 'tomato', 'basil', 'generic'] },
          height: { type: Type.NUMBER },
          leafCount: { type: Type.NUMBER },
          health: { type: Type.NUMBER },
        },
        required: ["type", "height", "leafCount", "health"]
      }
    }
  });

  const result = JSON.parse(response.text || '{}');
  return {
    ...result,
    lastUpdated: new Date().toISOString()
  };
}
