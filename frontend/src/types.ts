export interface ProductInput {
  name: string
  manufacturer: string | null
  specs: Record<string, string>
  description: string | null
}

export interface ExampleItem {
  id: string
  label: string
  product: ProductInput
}

export interface Characteristic {
  name: string
  value: string
}

export interface GenerateResponse {
  status: 'draft_ready' | 'needs_clarification'
  draft: {
    seo_title: string
    seo_description: string
    key_characteristics: Characteristic[]
    search_queries: string[]
    commercial_block: string
    markdown: string
  } | null
  missing_fields: string[]
  warnings: string[]
  quality: {
    grounded: boolean
    retry_count: number
  }
  request_id: string
}

export interface ApiErrorEnvelope {
  error?: {
    code?: string
    message?: string
    request_id?: string
  }
}

