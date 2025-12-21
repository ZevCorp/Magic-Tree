#!/bin/bash
# Quick script to start Magic Tree service
systemctl --user start magic-tree
echo "✅ Magic Tree service started"
echo "To stop: ./dev_stop.sh or systemctl --user stop magic-tree"
