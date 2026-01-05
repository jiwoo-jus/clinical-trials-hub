// src/utils/logger.js
// Development logging utility - only logs in development mode

const isDevelopment = process.env.NODE_ENV === 'development'; // eslint-disable-line no-undef

class Logger {
  constructor(context = 'App') {
    this.context = context;
  }

  log(...args) {
    if (isDevelopment) {
      console.log(`[${this.context}]`, ...args);
    }
  }

  info(...args) {
    if (isDevelopment) {
      console.info(`[${this.context}]`, ...args);
    }
  }

  warn(...args) {
    if (isDevelopment) {
      console.warn(`[${this.context}]`, ...args);
    }
  }

  error(...args) {
    // Always log errors, even in production
    console.error(`[${this.context}]`, ...args);
  }

  debug(...args) {
    if (isDevelopment) {
      console.debug(`[${this.context}]`, ...args);
    }
  }
}

// Create logger instances for different parts of the app
export const createLogger = (context) => new Logger(context);

// Pre-configured loggers for common use cases
export const apiLogger = new Logger('API');
export const searchLogger = new Logger('Search');
export const filterLogger = new Logger('Filter');
export const cacheLogger = new Logger('Cache');
export const detailLogger = new Logger('Detail');

export default Logger;
