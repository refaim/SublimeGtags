#include "linear_sequence.h"

#define BEFORE_FIRST_POS -1

typedef struct NodeStruct {
  struct NodeStruct *prev;
  struct NodeStruct *next;
  LSQ_BaseTypeT value;
} ListNodeT;

typedef struct {
  ListNodeT *beforeFirst;
  ListNodeT *pastRear;
  LSQ_IntegerIndexT size;
} ContainerT;

typedef struct {
  ContainerT *cHandle;
  ListNodeT *node;
} IteratorT;

/* Implementation */

LSQ_HandleT LSQ_CreateSequence(void) {
  ContainerT *newHandle = malloc(sizeof(ContainerT));
  newHandle->beforeFirst = malloc(sizeof(ListNodeT));
  newHandle->pastRear = malloc(sizeof(ListNodeT));
  newHandle->beforeFirst->prev = NULL;
  newHandle->beforeFirst->next = newHandle->pastRear;
  newHandle->beforeFirst->value = 0;
  newHandle->pastRear->prev = newHandle->beforeFirst;
  newHandle->pastRear->next = NULL;
  newHandle->pastRear->value = 0;
  newHandle->size = 0;
  return newHandle;
}

void LSQ_DestroySequence(LSQ_HandleT handle) {
  ContainerT *cHandle = handle;
  ListNodeT *currentNode = NULL, *nextNode = NULL;
  if (cHandle) {
    currentNode = cHandle->beforeFirst;
    do {
      nextNode = currentNode->next;
      free(currentNode);
      currentNode = nextNode;
    } while (currentNode);
  }
  free(handle);
}

LSQ_IntegerIndexT LSQ_GetSize(LSQ_HandleT handle) {
  return handle ? ((ContainerT *) handle)->size : 0;
}

int LSQ_IsIteratorDereferencable(LSQ_IteratorT iterator) {
  return iterator && !LSQ_IsIteratorBeforeFirst(iterator) && !LSQ_IsIteratorPastRear(iterator);
}

int LSQ_IsIteratorPastRear(LSQ_IteratorT iterator) {
  IteratorT *it = iterator;
  return iterator && (it->node == it->cHandle->pastRear);
}

int LSQ_IsIteratorBeforeFirst(LSQ_IteratorT iterator) {
  IteratorT *it = iterator;
  return iterator && (it->node == it->cHandle->beforeFirst);
}

LSQ_BaseTypeT* LSQ_DereferenceIterator(LSQ_IteratorT iterator) {
  IteratorT *it = iterator;
  return LSQ_IsIteratorDereferencable(iterator) ? &it->node->value : NULL;
}

LSQ_IteratorT LSQ_GetElementByIndex(LSQ_HandleT handle, LSQ_IntegerIndexT index) {
  IteratorT *newIt = NULL;
  ContainerT *cHandle = handle;
  if (cHandle && (index >= -1) && (index <= cHandle->size)) {
    newIt = malloc(sizeof(IteratorT));
    if (newIt) {
      newIt->cHandle = handle;
      LSQ_SetPosition(newIt, index);
    }
  }
  return newIt;
}

LSQ_IteratorT LSQ_GetFrontElement(LSQ_HandleT handle) {
  return LSQ_GetElementByIndex(handle, 0);
}

LSQ_IteratorT LSQ_GetPastRearElement(LSQ_HandleT handle) {
  return LSQ_GetElementByIndex(handle, LSQ_GetSize(handle));
}

void LSQ_DestroyIterator(LSQ_IteratorT iterator) {
  free(iterator);
}

void LSQ_AdvanceOneElement(LSQ_IteratorT iterator) {
  IteratorT *it = iterator;
  if (it && it->node && it->node->next)
    it->node = it->node->next;
}

void LSQ_RewindOneElement(LSQ_IteratorT iterator) {
  IteratorT *it = iterator;
  if (it && it->node && it->node->prev)
    it->node = it->node->prev;
}

void LSQ_ShiftPosition(LSQ_IteratorT iterator, LSQ_IntegerIndexT shift) {
  int i = 0;
  if (iterator) {
    if (shift > 0)
      for (i = 0; i < shift; i++)
        LSQ_AdvanceOneElement(iterator);
    else if (shift < 0)
      for (i = 0; i < -shift; i++)
        LSQ_RewindOneElement(iterator);
  }
}

void LSQ_SetPosition(LSQ_IteratorT iterator, LSQ_IntegerIndexT pos) {
  IteratorT *it = iterator;
  int i = BEFORE_FIRST_POS;
  if ((pos >= BEFORE_FIRST_POS) && (pos <= it->cHandle->size)) {
    it->node = it->cHandle->beforeFirst;
    for (i = BEFORE_FIRST_POS; i < pos ; i++)
      LSQ_AdvanceOneElement(it);
  }
}

void LSQ_InsertFrontElement(LSQ_HandleT handle, LSQ_BaseTypeT element) {
  IteratorT *it = LSQ_GetFrontElement(handle);
  LSQ_InsertElementBeforeGiven(it, element);
  LSQ_DestroyIterator(it);
}

void LSQ_InsertRearElement(LSQ_HandleT handle, LSQ_BaseTypeT element) {
  IteratorT *it = LSQ_GetPastRearElement(handle);
  LSQ_InsertElementBeforeGiven(it, element);
  LSQ_DestroyIterator(it);
}

void LSQ_InsertElementBeforeGiven(LSQ_IteratorT iterator, LSQ_BaseTypeT newElement) {
  IteratorT *it = iterator;
  ListNodeT *newNode = NULL;
  if (it && it->node && !LSQ_IsIteratorBeforeFirst(iterator)) {
    newNode = malloc(sizeof(ListNodeT));
    newNode->prev = it->node->prev;
    newNode->next = it->node;
    newNode->prev->next = newNode->next->prev = newNode;
    newNode->value = newElement;
    it->node = newNode;
    it->cHandle->size++;
  }
}

void LSQ_DeleteFrontElement(LSQ_HandleT handle) {
  IteratorT *it = LSQ_GetFrontElement(handle);
  LSQ_DeleteGivenElement(it);
  LSQ_DestroyIterator(it);
}

void LSQ_DeleteRearElement(LSQ_HandleT handle) {
  IteratorT *it = LSQ_GetPastRearElement(handle);
  LSQ_RewindOneElement(it);
  LSQ_DeleteGivenElement(it);
  LSQ_DestroyIterator(it);
}

void LSQ_DeleteGivenElement(LSQ_IteratorT iterator) {
  IteratorT *it = iterator;
  ListNodeT *targetNode = NULL;
  if (it && (it->cHandle->size != 0) && !LSQ_IsIteratorBeforeFirst(it) && !LSQ_IsIteratorPastRear(it)) {
    targetNode = it->node;
    it->node = it->node->next;
    targetNode->prev->next = targetNode->next;
    targetNode->next->prev = targetNode->prev;
    free(targetNode);
    it->cHandle->size--;
  }
}
