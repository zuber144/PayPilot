// src/components/ui/Toast.tsx
import React, { createContext, useContext, useState, useCallback } from 'react'

export interface ToastItem {
  id: string
  type: 'success' | 'error' | 'info' | 'warning'
  message: string
}

interface ToastContextValue {
  showToast: (message: string, type?: ToastItem['type']) => void
}

const ToastContext = createContext<ToastContextValue>({
  showToast: () => {},
})

export const useToast = () => useContext(ToastContext)

export const ToastProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [toasts, setToasts] = useState<ToastItem[]>([])

  const showToast = useCallback((message: string, type: ToastItem['type'] = 'info') => {
    const id = Math.random().toString(36).substring(2, 9)
    setToasts((prev) => [...prev, { id, type, message }])
    setTimeout(() => {
      setToasts((prev) => prev.filter((t) => t.id !== id))
    }, 4000)
  }, [])

  return (
    <ToastContext.Provider value={{ showToast }}>
      {children}
      {/* Toast container */}
      <div className="fixed bottom-4 right-4 z-50 flex flex-col gap-2 pointer-events-none max-w-sm w-full">
        {toasts.map((toast) => {
          const colorMap = {
            success: 'bg-emerald-600 text-white',
            error: 'bg-red-600 text-white',
            warning: 'bg-amber-600 text-white',
            info: 'bg-slate-800 text-white',
          }[toast.type]

          const iconMap = {
            success: '✓',
            error: '✕',
            warning: '⚠',
            info: 'ℹ',
          }[toast.type]

          return (
            <div
              key={toast.id}
              className={`pointer-events-auto flex items-center gap-3 px-4 py-3 rounded-lg shadow-lg text-sm transition-all animate-fade-in ${colorMap}`}
            >
              <span className="font-bold">{iconMap}</span>
              <p className="flex-1">{toast.message}</p>
            </div>
          )
        })}
      </div>
    </ToastContext.Provider>
  )
}
