export interface Module {
  id: string;
  name: string;
  description: string;
  icon: string;
  category: "core" | "integration" | "feature";
  requires?: string[];
  installSteps?: InstallStep[];
}

export interface InstallStep {
  title: string;
  description: string;
  type: "info" | "input" | "confirm";
  field?: string;
  placeholder?: string;
}

export interface ModuleStatus {
  id: string;
  installed: boolean;
  config?: Record<string, string>;
}

export interface FileEntry {
  name: string;
  type: "file" | "dir";
  size?: number;
  path: string;
}

export interface ChatMessage {
  role: "user" | "assistant";
  content: string;
  timestamp: string;
  toolUses?: string[];
}

export interface Stats {
  uptime: string;
  messagesReceived: number;
  messagesSent: number;
  errors: number;
  fileCount: number;
  dataSize: string;
  installedModules: string[];
}

export interface LogEntry {
  timestamp: string;
  level: "INFO" | "WARNING" | "ERROR";
  logger: string;
  message: string;
}

export interface Settings {
  model: string;
  mainLanguage: string;
  showTools: boolean;
}
