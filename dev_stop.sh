#!/bin/bash
# Quick script to stop Magic Tree service for development
systemctl --user stop magic-tree
echo "✅ Magic Tree service stopped"
echo "To start manually: ./run_test.sh"
echo "To re-enable service: systemctl --user start magic-tree"
