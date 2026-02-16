PYTHON ?= python

.PHONY: test test-unit lint clean install-dev

test: test-unit

test-unit:
	$(PYTHON) -c "import os,sys,unittest; sys.path[:0]=[os.getcwd(), os.path.join(os.getcwd(),'test')]; import test_zsi; result=unittest.TextTestRunner().run(test_zsi.makeTestSuite()); raise SystemExit(0 if result.wasSuccessful() else 1)"

lint:
	@echo "Lint placeholder: no linter configured yet."

clean:
	$(PYTHON) -c "import pathlib, shutil; [shutil.rmtree(p, ignore_errors=True) for p in pathlib.Path('.').glob('**/__pycache__')]; [p.unlink() for p in pathlib.Path('.').glob('**/*.py[co]') if p.is_file()]; [shutil.rmtree(pathlib.Path(d), ignore_errors=True) for d in ('build', 'dist', 'ZSI.egg-info')]"

install-dev:
	$(PYTHON) -m pip install -r requirements-dev.txt
