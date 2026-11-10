#!/bin/bash
# Run a command inside the restoration container (host-side orchestration helper).
exec limactl shell daedalus -- sudo docker exec -i daedalus bash -lc "$*"
