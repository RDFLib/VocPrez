import _config as conf
from data.source_RVA import RVA
from data.source_FILE import FILE
from data.source_VOCBENCH import VOCBENCH


def get_vocabulary(vocab_id):
    source_type = conf.VOCABS[vocab_id].get('source')

    if source_type == conf.VocabSource.FILE:
        v = FILE(vocab_id).get_vocabulary()
    elif source_type == conf.VocabSource.RVA:
        v = RVA(vocab_id).get_vocabulary()
    elif source_type == conf.VocabSource.VOCBENCH:
        v = VOCBENCH(vocab_id).get_vocabulary()
    # TODO: add other sources
    else:
        v = None

    return v


def get_object_class(vocab_id, uri):
    source_type = conf.VOCABS[vocab_id].get('source')

    if source_type == conf.VocabSource.FILE:
        c = FILE(vocab_id).get_object_class(uri)
    elif source_type == conf.VocabSource.RVA:
        c = RVA(vocab_id).get_object_class(uri)
    elif source_type == conf.VocabSource.VOCBENCH:
        c = VOCBENCH(vocab_id).get_object_class(uri)
    else:
        # no other sources for now
        c = None

    return c


def get_concept(vocab_id, uri):
    source_type = conf.VOCABS[vocab_id].get('source')

    if source_type == conf.VocabSource.FILE:
        c = FILE(vocab_id).get_concept(uri)
    elif source_type == conf.VocabSource.RVA:
        c = RVA(vocab_id).get_concept(uri)
    elif source_type == conf.VocabSource.VOCBENCH:
        c = VOCBENCH(vocab_id).get_concept(uri)
    else:
        # no other sources for now
        c = None

    return c


def list_concepts(vocab_id):
    source_type = conf.VOCABS[vocab_id].get('source')

    if source_type == conf.VocabSource.FILE:
        v = FILE(vocab_id).list_concepts()
    elif source_type == conf.VocabSource.RVA:
        v = RVA(vocab_id).list_concepts()
    elif source_type == conf.VocabSource.VOCBENCH:
        v = VOCBENCH(vocab_id).list_concepts()
    # TODO: add other sources
    else:
        v = None

    return v
