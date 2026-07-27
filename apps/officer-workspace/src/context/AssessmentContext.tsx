import { createContext, useContext, useEffect, useState, type ReactNode } from 'react';
import type { LiveAssessment } from '../types/workspace';

const STORAGE_KEY = 'mara_assessments';

interface AssessmentContextType {
  assessments: LiveAssessment[];
  addAssessment: (assessment: LiveAssessment) => void;
  updateAssessment: (threadId: string, patch: Partial<LiveAssessment>) => void;
  removeAssessment: (threadId: string) => void;
}

const AssessmentContext = createContext<AssessmentContextType | undefined>(undefined);

export function AssessmentProvider({ children }: { children: ReactNode }) {
  const [assessments, setAssessments] = useState<LiveAssessment[]>(() => {
    try {
      const saved = sessionStorage.getItem(STORAGE_KEY);
      return saved ? (JSON.parse(saved) as LiveAssessment[]) : [];
    } catch {
      return [];
    }
  });

  useEffect(() => {
    sessionStorage.setItem(STORAGE_KEY, JSON.stringify(assessments));
  }, [assessments]);

  function addAssessment(assessment: LiveAssessment) {
    setAssessments((prev) => [assessment, ...prev]);
  }

  function updateAssessment(threadId: string, patch: Partial<LiveAssessment>) {
    setAssessments((prev) =>
      prev.map((a) => (a.thread_id === threadId ? { ...a, ...patch } : a)),
    );
  }

  function removeAssessment(threadId: string) {
    setAssessments((prev) => prev.filter((a) => a.thread_id !== threadId));
  }

  return (
    <AssessmentContext.Provider value={{ assessments, addAssessment, updateAssessment, removeAssessment }}>
      {children}
    </AssessmentContext.Provider>
  );
}

export function useAssessments() {
  const context = useContext(AssessmentContext);
  if (!context) {
    throw new Error('useAssessments must be used within an AssessmentProvider');
  }
  return context;
}
