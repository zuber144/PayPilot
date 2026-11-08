// src/api/index.ts — exports the active API client based on VITE_USE_MOCKS

import { realClient } from './client'
import { mockClient } from '../mocks/mockClient'

const useMocks = import.meta.env.VITE_USE_MOCKS === 'true'

export const api = useMocks ? mockClient : realClient
export type ApiClient = typeof realClient
