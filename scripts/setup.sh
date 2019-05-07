mkdir -p happy_path
touch happy_path/a.py
touch happy_path/b.py
touch happy_path/c.py
mkdir -p multi_dir/a
touch multi_dir/a/a1.py
touch multi_dir/a/a2.py
mkdir -p multi_dir/b
touch multi_dir/b/b1.py
mkdir -p multi_dir/c
touch multi_dir/c/c1.py
touch multi_dir/c/c2.py
mkdir -p dependencies/dir/sub-dir
touch dependencies/dir/a.py
touch dependencies/dir/b.py
touch dependencies/dir/sub-dir/c.py
touch dependencies/dir/sub-dir/d.py
touch dependencies/dir/sub-dir/e.py
mkdir -p local/then_this
touch local/then_this/c1.py
mkdir -p local/this_first/dir/sub1
touch local/this_first/dir/sub1/b1.py
mkdir -p local/this_first/dir/sub2
touch local/this_first/dir/sub2/a1.py
touch local/this_first/dir/sub2/a2.py
touch local/this_first/dir/sub2/a3.py
