import { CapabilityHandlerMap } from "./handlers";
import { SelectedObject } from "../selection/selectionLogic";
import { RuntimeState } from "../bootstrap/state";

export interface CapabilityServices {
  runBootstrapSequence?: () => Promise<any>;
}

export interface CapabilityContext {
  selectedObjects: SelectedObject[];
  referenceObject?: SelectedObject;
  args?: Record<string, any>;
  runtimeState?: RuntimeState;
  services?: CapabilityServices;
}

export interface CapabilityResult {
  success: boolean;
  message: string;
  data?: any;
}

export class UdiDispatcher {
  private handlers: CapabilityHandlerMap;

  constructor(handlers: CapabilityHandlerMap) {
    this.handlers = handlers;
  }
 

  async execute(
    capabilityId: string,
    context: CapabilityContext
  ): Promise<CapabilityResult> {
    const handler = this.handlers[capabilityId];

    if (!handler) {
      return {
        success: false,
        message: `No handler registered for capability: ${capabilityId}`,
      };
    }

    try {
      const result = await handler(context);
      return {
        success: true,
        message: `Capability ${capabilityId} executed successfully.`,
        data: result,
      };
    } catch (err: any) {
      return {
        success: false,
        message: `Capability ${capabilityId} failed: ${err.message}`,
      };
    }
  }
}
