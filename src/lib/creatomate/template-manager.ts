import fs from 'fs';
import path from 'path';

interface TemplateConfig {
    id: string;
    name: string;
    modifications: Record<string, any>;
}

export class TemplateManager {
    private templateDir: string;

    constructor() {
        this.templateDir = path.join(process.cwd(), 'src', 'lib', 'creatomate', 'templates');
    }

    getTemplate(templateName: string): TemplateConfig | null {
        try {
            const filePath = path.join(this.templateDir, `${templateName}.json`);
            if (!fs.existsSync(filePath)) {
                return null;
            }
            const fileContent = fs.readFileSync(filePath, 'utf-8');
            return JSON.parse(fileContent);
        } catch (error) {
            console.error(`Error loading template ${templateName}:`, error);
            return null;
        }
    }

    applyTemplate(template: TemplateConfig, data: any): Record<string, any> {
        const modifications: Record<string, any> = {};

        for (const [key, value] of Object.entries(template.modifications)) {
            if (typeof value === 'string') {
                // Simple regex to replace {{key}} with data[key]
                // Supports nested keys like {{mediaUrls.mainVideo}}
                modifications[key] = value.replace(/\{\{([^}]+)\}\}/g, (_, path) => {
                    const val = path.split('.').reduce((obj: any, k: string) => (obj || {})[k], data);
                    return val !== undefined && val !== null ? val : '';
                });
            } else {
                modifications[key] = value;
            }
        }

        return modifications;
    }
}
