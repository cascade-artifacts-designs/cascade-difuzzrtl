# Copyright 2023 Flavien Solt, ETH Zurich.
# Licensed under the General Public License, Version 3.0, see LICENSE for details.
# SPDX-License-Identifier: GPL-3.0-only

build:
	docker build -t difuzzrtl-img .

run:
	docker run -it -v $(CASCADE_DOCKER_MNT_DIR):/difuzzrtl difuzzrtl-img
