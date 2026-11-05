import { fireEvent, render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it, vi } from 'vitest'

import App from './App'

const example = {
  id: 'testo-510.partial',
  label: 'testo 510 — недостаточно данных',
  product: {
    name: 'testo 510',
    manufacturer: 'Testo',
    specs: { 'Диапазон измерений': '0 ... 100 гПа' },
    description: null,
  },
}

describe('App', () => {
  afterEach(() => vi.unstubAllGlobals())

  it('loads a demonstration example into the form', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: true, json: async () => [example] }))
    render(<App />)
    await userEvent.selectOptions(await screen.findByLabelText('Демонстрационный пример'), example.id)
    expect(screen.getByDisplayValue('testo 510')).toBeInTheDocument()
    expect(screen.getByDisplayValue('0 ... 100 гПа')).toBeInTheDocument()
  })

  it('keeps invalid JSON in the editor and shows an error', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: true, json: async () => [] }))
    render(<App />)
    await userEvent.click(screen.getByRole('button', { name: 'JSON' }))
    const editor = screen.getByLabelText('JSON товара')
    fireEvent.change(editor, { target: { value: '{{' } })
    await userEvent.click(screen.getByRole('button', { name: 'Форма' }))
    expect(screen.getByText('Некорректный JSON')).toBeInTheDocument()
    expect(editor).toHaveValue('{{')
  })

  it('shows clarification guidance when no grounded draft was produced', async () => {
    vi.stubGlobal('fetch', vi.fn(async (input: RequestInfo | URL) => {
      if (String(input).endsWith('/api/v1/examples')) {
        return { ok: true, json: async () => [example] }
      }
      return {
        ok: true,
        json: async () => ({
          status: 'needs_clarification',
          draft: null,
          missing_fields: ['description'],
          warnings: ['Дополните отсутствующие поля и повторите генерацию'],
          quality: { grounded: false, retry_count: 1 },
          request_id: 'request-1',
        }),
      }
    }))
    render(<App />)
    await userEvent.selectOptions(await screen.findByLabelText('Демонстрационный пример'), example.id)
    await userEvent.click(screen.getByRole('button', { name: 'Сгенерировать черновик' }))
    expect(await screen.findByText('Проверенный черновик не сформирован.')).toBeInTheDocument()
    expect(screen.getByText(/описание/)).toBeInTheDocument()
  })
})

