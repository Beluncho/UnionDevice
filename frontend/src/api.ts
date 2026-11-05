import type { ApiErrorEnvelope, ExampleItem, GenerateResponse, ProductInput } from './types'

async function readError(response: Response): Promise<string> {
  try {
    const payload = (await response.json()) as ApiErrorEnvelope
    return payload.error?.message || `Ошибка API: ${response.status}`
  } catch {
    return `Ошибка API: ${response.status}`
  }
}

export async function fetchExamples(): Promise<ExampleItem[]> {
  const response = await fetch('/api/v1/examples')
  if (!response.ok) throw new Error(await readError(response))
  return (await response.json()) as ExampleItem[]
}

export async function generateProductCard(product: ProductInput): Promise<GenerateResponse> {
  const response = await fetch('/api/v1/product-cards/generate', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(product),
  })
  if (!response.ok) throw new Error(await readError(response))
  return (await response.json()) as GenerateResponse
}

