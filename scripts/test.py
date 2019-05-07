import os
from create_incr_tickets import Batch, crawl

BASE = os.getcwd()


def test_dirs():

    batch = Batch('root')
    files = [
        'food/fruit/berries/blueberries.py',
        'food/fruit/berries/blackberries.py',
        'food/fruit/apples.py',
        'food/fruit/bananas.py',
        'furniture/chair.py',
        'furniture/table.py'
    ]

    for f in files:
        batch.add(f)
    expected_dirs = [
        'food/fruit',
        'food/fruit/berries',
        'furniture'
    ]
    assert batch.directories == expected_dirs

    expected_dirs = ['food/fruit', 'furniture']
    assert batch.top_level_directories == expected_dirs


def test_rebalanced_root():

    batch = Batch('food/fruit/berries')
    batch.add('food/fruit/berries/raspberries.py')
    assert batch.root == 'food/fruit/berries'
    batch.add('food/fruit/apples.py')
    assert batch.root == 'food/fruit'
    batch.add('food/meat/poultry/chicken.py')
    assert batch.root == 'food'


def test_crawl_happy_path():
    PATH = os.path.join(BASE, 'happy_path')
    batches = crawl(PATH, 3)
    assert len(batches) == 1
    batch = batches[0]
    assert len(batch.files) == 3
    assert batch.root == PATH


def test_crawl_multidir():
    PATH = os.path.join(BASE, 'multi_dir')
    batches = crawl(PATH, 3)
    assert len(batches) == 2
    complete_batch = batches[0]
    assert len(complete_batch.files) == 3
    assert complete_batch.root == PATH
    incomplete_batch = batches[1]
    assert len(incomplete_batch.files) == 2
    assert incomplete_batch.root == PATH + '/a'


def test_crawl_w_dependencies():
    PATH = os.path.join(BASE, 'dependencies')
    batches = crawl(PATH, 3)
    assert len(batches) == 2
    complete_batch = batches[0]
    assert len(complete_batch.files) == 3
    assert complete_batch.root == PATH + '/dir/sub-dir'
    assert not complete_batch.blocked
    incomplete_batch = batches[1]
    assert len(incomplete_batch.files) == 2
    assert incomplete_batch.root == PATH + '/dir'
    assert incomplete_batch.blocked


def test_local_batches():
    PATH = os.path.join(BASE, 'local')
    batches = crawl(PATH, 3)
    assert len(batches) == 3
    first_batch = batches[0]
    assert len(first_batch.files) == 3
    assert first_batch.root == PATH + "/this_first/dir/sub2"
    second_batch = batches[1]
    assert len(second_batch.files) == 1
    assert second_batch.root == PATH + "/this_first/dir/sub1"
    third_batch = batches[2]
    assert len(third_batch.files) == 1
    assert third_batch.root == PATH + "/then_this"
