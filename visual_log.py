#!/usr/bin/env python3
"""
Visual Log Window for Magic Tree
Shows a floating window with real-time logs during startup.
Uses tkinter for maximum compatibility (no external dependencies).
"""

import tkinter as tk
from tkinter import scrolledtext
import threading
import queue
import time
import logging
import os

class VisualLogWindow:
    """A floating window that displays logs in real-time."""
    
    def __init__(self, title="Magic Tree - Startup Log", auto_close_seconds=60):
        self.title = title
        self.auto_close_seconds = auto_close_seconds
        self.running = False
        self.log_queue = queue.Queue()
        self.window = None
        self.start_time = time.time()
        
    def start(self):
        """Start the log window in a separate thread."""
        self.running = True
        self.window_thread = threading.Thread(target=self._run_window, daemon=True)
        self.window_thread.start()
        # Give window time to initialize
        time.sleep(0.5)
        
    def _run_window(self):
        """Run the tkinter window (must be in its own thread)."""
        try:
            self.window = tk.Tk()
            self.window.title(self.title)
            
            # Window properties - semi-transparent, always on top
            self.window.geometry("900x400+50+50")
            self.window.configure(bg='#1a1a2e')
            self.window.attributes('-topmost', True)
            
            # Title label
            title_label = tk.Label(
                self.window, 
                text="🎄 Magic Tree - Log de Inicio 🎄",
                font=("Helvetica", 14, "bold"),
                fg="#00ff88",
                bg="#1a1a2e"
            )
            title_label.pack(pady=5)
            
            # Status label
            self.status_label = tk.Label(
                self.window,
                text="Iniciando...",
                font=("Helvetica", 10),
                fg="#ffcc00",
                bg="#1a1a2e"
            )
            self.status_label.pack()
            
            # Scrolled text area for logs
            self.text_area = scrolledtext.ScrolledText(
                self.window,
                wrap=tk.WORD,
                font=("Courier", 9),
                bg="#0a0a14",
                fg="#00ff88",
                insertbackground="#00ff88"
            )
            self.text_area.pack(expand=True, fill='both', padx=10, pady=10)
            
            # Close button
            close_btn = tk.Button(
                self.window,
                text="Cerrar Log (continuará en background)",
                command=self.stop,
                bg="#ff4444",
                fg="white",
                font=("Helvetica", 10)
            )
            close_btn.pack(pady=5)
            
            # Start update loop
            self._update_log()
            
            self.window.mainloop()
            
        except Exception as e:
            print(f"Error creating log window: {e}")
            self.running = False
    
    def _update_log(self):
        """Update the log display from the queue."""
        if not self.running:
            return
            
        try:
            # Process all pending log messages
            while True:
                try:
                    msg = self.log_queue.get_nowait()
                    self.text_area.insert(tk.END, msg + "\n")
                    self.text_area.see(tk.END)  # Auto-scroll
                except queue.Empty:
                    break
            
            # Update status with elapsed time
            elapsed = int(time.time() - self.start_time)
            remaining = max(0, self.auto_close_seconds - elapsed)
            self.status_label.config(
                text=f"Tiempo: {elapsed}s | Auto-cerrar en: {remaining}s"
            )
            
            # Auto-close after timeout
            if elapsed >= self.auto_close_seconds:
                self.stop()
                return
            
            # Schedule next update
            if self.window:
                self.window.after(100, self._update_log)
                
        except Exception:
            pass
    
    def log(self, message):
        """Add a message to the log queue."""
        timestamp = time.strftime("%H:%M:%S")
        self.log_queue.put(f"[{timestamp}] {message}")
    
    def set_status(self, status):
        """Update the status text."""
        try:
            if self.status_label:
                self.status_label.config(text=status)
        except:
            pass
    
    def stop(self):
        """Close the log window."""
        self.running = False
        try:
            if self.window:
                self.window.destroy()
        except:
            pass


class LogWindowHandler(logging.Handler):
    """Logging handler that sends logs to the visual window."""
    
    def __init__(self, visual_log):
        super().__init__()
        self.visual_log = visual_log
        
    def emit(self, record):
        try:
            msg = self.format(record)
            self.visual_log.log(msg)
        except:
            pass


def create_startup_log_window():
    """Create and return a visual log window."""
    log_window = VisualLogWindow(auto_close_seconds=30)
    log_window.start()
    return log_window


# Test/Demo
if __name__ == "__main__":
    print("Testing Visual Log Window...")
    
    log_window = create_startup_log_window()
    
    # Add some test messages
    for i in range(20):
        log_window.log(f"Test message {i+1}: System initializing...")
        time.sleep(0.5)
    
    log_window.log("✓ All systems ready!")
    log_window.set_status("Ready - Window will close in 5 seconds")
    
    time.sleep(5)
    log_window.stop()
    print("Test complete!")
