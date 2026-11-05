import { useEffect, useMemo, useState } from 'react'

import { fetchExamples, generateProductCard } from './api'
import type { ExampleItem, GenerateResponse, ProductInput } from './types'

const EMPTY_PRODUCT: ProductInput = {
  name: '',
  manufacturer: null,
  specs: {},
  description: null,
}

const FIELD_LABELS: Record<string, string> = {
  manufacturer: 'производитель',
  specs: 'характеристики',
  description: 'описание',
}

function normalizeProduct(value: unknown): ProductInput {
  if (!value || typeof value !== 'object') throw new Error('JSON должен содержать объект товара')
  const raw = value as Partial<ProductInput>
  if (typeof raw.name !== 'string') throw new Error('Поле name должно быть строкой')
  if (raw.manufacturer !== null && raw.manufacturer !== undefined && typeof raw.manufacturer !== 'string') {
    throw new Error('Поле manufacturer должно быть строкой или null')
  }
  if (!raw.specs || typeof raw.specs !== 'object' || Array.isArray(raw.specs)) {
    throw new Error('Поле specs должно быть объектом')
  }
  const specs: Record<string, string> = {}
  for (const [key, item] of Object.entries(raw.specs)) {
    if (typeof item !== 'string') throw new Error('Значения specs должны быть строками')
    specs[key] = item
  }
  if (raw.description !== null && raw.description !== undefined && typeof raw.description !== 'string') {
    throw new Error('Поле description должно быть строкой или null')
  }
  return {
    name: raw.name,
    manufacturer: raw.manufacturer ?? null,
    specs,
    description: raw.description ?? null,
  }
}

function jsonErrorMessage(reason: unknown): string {
  if (reason instanceof SyntaxError) return 'Некорректный JSON'
  return reason instanceof Error ? reason.message : 'Некорректный JSON'
}

export default function App() {
  const [mode, setMode] = useState<'form' | 'json'>('form')
  const [product, setProduct] = useState<ProductInput>(EMPTY_PRODUCT)
  const [jsonText, setJsonText] = useState(JSON.stringify(EMPTY_PRODUCT, null, 2))
  const [jsonError, setJsonError] = useState<string | null>(null)
  const [examples, setExamples] = useState<ExampleItem[]>([])
  const [result, setResult] = useState<GenerateResponse | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)
  const [copied, setCopied] = useState<string | null>(null)

  useEffect(() => {
    fetchExamples().then(setExamples).catch((reason: Error) => setError(reason.message))
  }, [])

  const specEntries = useMemo(() => Object.entries(product.specs), [product.specs])

  function changeMode(next: 'form' | 'json') {
    if (next === 'json') {
      setJsonText(JSON.stringify(product, null, 2))
      setJsonError(null)
      setMode(next)
      return
    }
    try {
      const parsed = normalizeProduct(JSON.parse(jsonText))
      setProduct(parsed)
      setJsonError(null)
      setMode(next)
    } catch (reason) {
      setJsonError(jsonErrorMessage(reason))
    }
  }

  function loadExample(id: string) {
    const example = examples.find((item) => item.id === id)
    if (!example) return
    setProduct(example.product)
    setJsonText(JSON.stringify(example.product, null, 2))
    setResult(null)
    setError(null)
    setJsonError(null)
  }

  function updateSpec(index: number, key: string, value: string) {
    const entries = [...specEntries]
    entries[index] = [key, value]
    setProduct((current) => ({ ...current, specs: Object.fromEntries(entries) }))
  }

  function removeSpec(index: number) {
    setProduct((current) => ({
      ...current,
      specs: Object.fromEntries(Object.entries(current.specs).filter((_, itemIndex) => itemIndex !== index)),
    }))
  }

  async function submit() {
    setError(null)
    setResult(null)
    let payload = product
    if (mode === 'json') {
      try {
        payload = normalizeProduct(JSON.parse(jsonText))
        setProduct(payload)
        setJsonError(null)
      } catch (reason) {
        setJsonError(jsonErrorMessage(reason))
        return
      }
    }
    if (!payload.name.trim()) {
      setError('Укажите название товара')
      return
    }
    if (!payload.description?.trim() && Object.keys(payload.specs).length === 0) {
      setError('Добавьте описание или хотя бы одну характеристику')
      return
    }
    setLoading(true)
    try {
      setResult(await generateProductCard(payload))
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Не удалось получить результат')
    } finally {
      setLoading(false)
    }
  }

  async function copy(label: string, value: string) {
    await navigator.clipboard.writeText(value)
    setCopied(label)
    window.setTimeout(() => setCopied(null), 1500)
  }

  return (
    <main className="app-shell">
      <header className="hero">
        <p className="eyebrow">B2B · AI content assistant</p>
        <h1>Черновик карточки прибора — из подтверждённых данных</h1>
        <p className="hero-copy">
          Сервис структурирует характеристики и создаёт SEO-текст, не добавляя технические
          значения, которых нет во входе.
        </p>
      </header>

      <section className="workspace" aria-label="Генератор карточки товара">
        <div className="panel input-panel">
          <div className="panel-heading">
            <div>
              <span className="step">01</span>
              <h2>Исходные данные</h2>
            </div>
            <select aria-label="Демонстрационный пример" defaultValue="" onChange={(event) => loadExample(event.target.value)}>
              <option value="" disabled>Выбрать пример</option>
              {examples.map((example) => <option key={example.id} value={example.id}>{example.label}</option>)}
            </select>
          </div>

          <div className="mode-switch" role="group" aria-label="Режим ввода">
            <button className={mode === 'form' ? 'active' : ''} onClick={() => changeMode('form')}>Форма</button>
            <button className={mode === 'json' ? 'active' : ''} onClick={() => changeMode('json')}>JSON</button>
          </div>

          {mode === 'form' ? (
            <div className="form-grid">
              <label>
                Название товара <span aria-hidden="true">*</span>
                <input value={product.name} onChange={(event) => setProduct({ ...product, name: event.target.value })} placeholder="Например, testo 510" />
              </label>
              <label>
                Производитель
                <input value={product.manufacturer ?? ''} onChange={(event) => setProduct({ ...product, manufacturer: event.target.value || null })} placeholder="Testo" />
              </label>
              <label className="wide">
                Описание или фрагмент паспорта
                <textarea value={product.description ?? ''} onChange={(event) => setProduct({ ...product, description: event.target.value || null })} rows={7} placeholder="Назначение, условия применения и подтверждённые сведения" />
              </label>
              <div className="wide specs-block">
                <div className="section-label">
                  <span>Характеристики</span>
                  <button className="text-button" onClick={() => setProduct({ ...product, specs: { ...product.specs, '': '' } })}>+ Добавить</button>
                </div>
                {specEntries.length === 0 && <p className="empty-note">Характеристики пока не добавлены.</p>}
                {specEntries.map(([key, value], index) => (
                  <div className="spec-row" key={`${index}-${key}`}>
                    <input aria-label={`Название характеристики ${index + 1}`} value={key} onChange={(event) => updateSpec(index, event.target.value, value)} placeholder="Диапазон измерений" />
                    <input aria-label={`Значение характеристики ${index + 1}`} value={value} onChange={(event) => updateSpec(index, key, event.target.value)} placeholder="0 ... 100 гПа" />
                    <button className="icon-button" aria-label={`Удалить характеристику ${index + 1}`} onClick={() => removeSpec(index)}>×</button>
                  </div>
                ))}
              </div>
            </div>
          ) : (
            <label className="json-editor">
              JSON товара
              <textarea value={jsonText} onChange={(event) => setJsonText(event.target.value)} rows={22} spellCheck={false} />
              {jsonError && <span className="field-error">{jsonError}</span>}
            </label>
          )}

          {error && <div className="alert error" role="alert">{error}</div>}
          <button className="primary-button" disabled={loading} onClick={submit}>
            {loading ? 'Проверяем и генерируем…' : 'Сгенерировать черновик'}
          </button>
          <p className="privacy-note">Данные отправляются только настроенному LLM-провайдеру. Результат не сохраняется.</p>
        </div>

        <div className="panel output-panel" aria-live="polite">
          <div className="panel-heading">
            <div>
              <span className="step">02</span>
              <h2>Результат</h2>
            </div>
            {result && <span className={`status ${result.status}`}>{result.status === 'draft_ready' ? 'Черновик готов' : 'Нужно уточнение'}</span>}
          </div>

          {!result ? (
            <div className="result-placeholder">
              <span>AI</span>
              <h3>Здесь появится проверенный черновик</h3>
              <p>Выберите демонстрационный пример или заполните данные вручную.</p>
            </div>
          ) : result.draft ? (
            <article className="result-card">
              {result.status === 'needs_clarification' && (
                <div className="alert warning">
                  <strong>Недостаточно исходных данных.</strong>
                  <span>Уточните: {result.missing_fields.map((field) => FIELD_LABELS[field] ?? field).join(', ')}.</span>
                </div>
              )}
              <section><span className="result-label">SEO-заголовок · {result.draft.seo_title.length}/70</span><h3>{result.draft.seo_title}</h3></section>
              <section><span className="result-label">SEO-описание · {result.draft.seo_description.length} символов</span><p>{result.draft.seo_description}</p></section>
              <section><span className="result-label">Ключевые характеристики</span><dl>{result.draft.key_characteristics.map((item) => <div key={item.name}><dt>{item.name}</dt><dd>{item.value}</dd></div>)}</dl></section>
              <section><span className="result-label">Поисковые запросы</span><div className="tags">{result.draft.search_queries.map((query) => <span key={query}>{query}</span>)}</div></section>
              <section><span className="result-label">Для менеджера</span><p>{result.draft.commercial_block}</p></section>
              <div className="result-actions">
                <button onClick={() => copy('json', JSON.stringify(result, null, 2))}>{copied === 'json' ? 'Скопировано' : 'Копировать JSON'}</button>
                <button onClick={() => result.draft && copy('markdown', result.draft.markdown)}>{copied === 'markdown' ? 'Скопировано' : 'Копировать Markdown'}</button>
              </div>
              <footer>Grounding: пройден · попыток коррекции: {result.quality.retry_count} · ID: {result.request_id}</footer>
            </article>
          ) : (
            <article className="result-card clarification-card">
              <div className="alert warning">
                <strong>Проверенный черновик не сформирован.</strong>
                <span>Уточните: {result.missing_fields.map((field) => FIELD_LABELS[field] ?? field).join(', ')}.</span>
              </div>
              <section>
                <span className="result-label">Что делать дальше</span>
                <h3>Дополните исходные данные и повторите генерацию</h3>
                {result.warnings.map((warning) => <p key={warning}>{warning}</p>)}
              </section>
              <footer>Grounding: не пройден · попыток коррекции: {result.quality.retry_count} · ID: {result.request_id}</footer>
            </article>
          )}
        </div>
      </section>
    </main>
  )
}

