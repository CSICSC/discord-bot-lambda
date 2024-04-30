rm lambda_function.zip
zip -r lambda_function.zip . -x .env -x .gitignore -x '.git*' -x lambda_test.py -x zip.bash -x '__*' -x 'tmp'